import asyncio
import json
import os
import time
from dotenv import load_dotenv

from livekit.agents import (
    Agent, 
    AgentSession, 
    JobContext, 
    cli, 
    function_tool, 
    JobProcess, 
    WorkerOptions,
    room_io
)
from livekit.plugins import openai, silero
from livekit.plugins import ai_coustics


load_dotenv()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    config = json.loads(participant.metadata)
    
    system_prompt = config["systemPrompt"]
    first_message = config["firstMessage"]
    print(system_prompt)
    print(first_message)

    interview_start_time = time.time()
    # State tracking for the silence watcher
    silence_task: asyncio.Task | None = None
    silence_stage = 0
    is_nudging = False

    # =========================================================================
    # TOOLS
    # =========================================================================

    @function_tool
    async def check_time_remaining() -> str:
        """Call this to check elapsed time. The target interview length is 10 minutes."""
        elapsed_seconds = time.time() - interview_start_time
        mins, secs = int(elapsed_seconds // 60), int(elapsed_seconds % 60)
        return f"{mins}m {secs}s elapsed."

    @function_tool
    async def end_interview() -> str:
        """Call this function to end the interview. Use ONLY after you have said your final goodbye."""
        cancel_silence_watcher()
        await asyncio.sleep(2)
        await ctx.room.disconnect()
        return "Disconnected"

    # =========================================================================
    # MODEL & AGENT SETUP
    # =========================================================================
    model = openai.realtime.RealtimeModel.with_azure(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"), # type: ignore
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION"),
    )

    interviewer_agent = Agent(
        instructions=system_prompt,
        tools=[check_time_remaining, end_interview],
    )

    session = AgentSession(
        llm=model,
        vad=silero.VAD.load(),
    )

    silence_task: asyncio.Task | None = None
    silence_stage = 0
    is_nudging = False

    def cancel_silence_watcher():
        nonlocal silence_task
        if silence_task and not silence_task.done():
            silence_task.cancel()
        silence_task = None

    def reset_silence_watcher(reset_stage=True):
        nonlocal silence_task, silence_stage
        if reset_stage:
            silence_stage = 0
        cancel_silence_watcher()
        silence_task = asyncio.create_task(_silence_watcher())

    async def _silence_watcher():
        nonlocal silence_stage, is_nudging
        try:
            if silence_stage == 0:
                await asyncio.sleep(8)
                silence_stage = 1
                is_nudging = True
                print("🎙️ [SILENCE] Stage 0 -> 1 (Nudge 1)")
                await session.generate_reply(instructions="The candidate has been silent for a while. Say something warm and brief like: 'Take your time, there's no rush.' Just one short sentence.")
            elif silence_stage == 1:
                await asyncio.sleep(8)
                silence_stage = 2
                is_nudging = True
                print("🎙️ [SILENCE] Stage 1 -> 2 (Nudge 2)")
                await session.generate_reply(instructions="The candidate is still silent. Say: 'Are you still there? I can repeat the question if that helps.' One sentence only.")
            elif silence_stage == 2:
                await asyncio.sleep(10)
                silence_stage = 3
                is_nudging = True
                print("🎙️ [SILENCE] Stage 2 -> 3 (End)")
                await session.generate_reply(instructions="The candidate has not responded for a long time. End the session gracefully. Say exactly: 'It seems like we may have lost you — no worries at all. Our team will reach out to reschedule. Thanks for your time, goodbye!' Then immediately call the end_interview tool.")
        except asyncio.CancelledError:
            pass

    # --- Event Listeners ---
    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        state_str = str(ev.new_state).lower()
        if "speaking" in state_str:
            print("🎙️ [EVENT] User started speaking! Cancelling timer.")
            cancel_silence_watcher()

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        state_str = str(ev.new_state).lower()
        old_state_str = str(ev.old_state).lower()
        print(f"🤖 [EVENT] Agent state: {old_state_str} -> {state_str}")
        if "listening" in state_str:
            nonlocal is_nudging
            if is_nudging:
                is_nudging = False
                reset_silence_watcher(reset_stage=False)
            else:
                reset_silence_watcher(reset_stage=True)
        else:
            cancel_silence_watcher()
    
    # =========================================================================
    # START SESSION
    # =========================================================================
    await session.start(
        agent=interviewer_agent, 
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(model=ai_coustics.EnhancerModel.QUAIL_L),
            ),
        ),
    )

    await session.generate_reply(
        instructions = f"Begin the interview now. Your opening line is: {first_message}"
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm
    ))