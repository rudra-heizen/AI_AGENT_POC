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
from livekit.plugins import openai, deepgram
from livekit.plugins import ai_coustics


load_dotenv()


def prewarm(proc: JobProcess):
    pass


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    config = json.loads(participant.metadata)

    system_prompt = config["systemPrompt"]
    first_message = config["firstMessage"]
    print(system_prompt)
    print(first_message)

    interview_start_time = time.time()
    silence_task: asyncio.Task | None = None
    pending_silence_task: asyncio.Task | None = None
    silence_stage = 0
    is_nudging = False
    agent_is_speaking = False
    interview_ended = False

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
        nonlocal interview_ended
        interview_ended = True
        cancel_silence_watcher()
        cancel_pending_silence()
        # 4s gives the goodbye audio time to fully play before disconnecting,
        # preventing the silence watcher from firing a second goodbye.
        await asyncio.sleep(4)
        await ctx.room.disconnect()
        return "Disconnected"

    # =========================================================================
    # MODEL & AGENT SETUP
    # =========================================================================

    model = openai.realtime.RealtimeModel.with_azure(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),  # type: ignore
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION"),
        turn_detection=None,
    )

    interviewer_agent = Agent(
        instructions=system_prompt,
        tools=[check_time_remaining, end_interview],
    )

    session = AgentSession(
        stt=deepgram.STT(
            model="nova-2",
            language="en-US",
            # 500ms: long enough to absorb breath pauses and prevent
            # single-word hallucinations, short enough to feel responsive.
            endpointing_ms=500,
            interim_results=False,
        ),
        llm=model,
        vad=ai_coustics.VAD(),
        allow_interruptions=True,
    )

    # =========================================================================
    # SILENCE WATCHER
    #
    # Two-phase design:
    #   Phase 1 — "pending" (2.5s): absorbs Realtime API chunk gaps where
    #             the agent briefly touches "listening" mid-response.
    #             If agent resumes speaking within 2.5s, arm is cancelled.
    #   Phase 2 — "active": nudge/end logic runs only after confirmed silence.
    # =========================================================================

    def cancel_silence_watcher():
        nonlocal silence_task
        if silence_task and not silence_task.done():
            silence_task.cancel()
        silence_task = None

    def cancel_pending_silence():
        nonlocal pending_silence_task
        if pending_silence_task and not pending_silence_task.done():
            pending_silence_task.cancel()
        pending_silence_task = None

    def reset_silence_watcher(reset_stage=True):
        nonlocal silence_task, silence_stage
        if reset_stage:
            silence_stage = 0
        cancel_silence_watcher()
        silence_task = asyncio.create_task(_silence_watcher())

    def arm_silence_watcher_delayed(reset_stage=True):
        """
        Waits 2.5s before arming the silence watcher.
        Prevents firing during Realtime API chunk gaps (e.g. after
        'Next question:' before the question itself is streamed).
        Cancelled immediately if agent resumes speaking.
        """
        cancel_pending_silence()
        cancel_silence_watcher()

        async def _arm():
            try:
                await asyncio.sleep(2.5)
                if not interview_ended:
                    print("⏱️ [SILENCE] Pending delay passed — arming watcher")
                    reset_silence_watcher(reset_stage=reset_stage)
            except asyncio.CancelledError:
                print("⏱️ [SILENCE] Pending arm cancelled — agent resumed speaking")

        nonlocal pending_silence_task
        pending_silence_task = asyncio.create_task(_arm())

    async def _silence_watcher():
        nonlocal silence_stage, is_nudging
        try:
            if interview_ended:
                return

            if silence_stage == 0:
                await asyncio.sleep(8)
                if interview_ended:
                    return
                silence_stage = 1
                is_nudging = True
                print("🎙️ [SILENCE] Stage 0 -> 1 (Nudge 1)")
                await session.generate_reply(
                    instructions="The candidate has been silent for a while. Say something warm and brief like: 'Take your time, there's no rush.' Just one short sentence."
                )
            elif silence_stage == 1:
                await asyncio.sleep(8)
                if interview_ended:
                    return
                silence_stage = 2
                is_nudging = True
                print("🎙️ [SILENCE] Stage 1 -> 2 (Nudge 2)")
                await session.generate_reply(
                    instructions="The candidate is still silent. Say: 'Are you still there? I can repeat the question if that helps.' One sentence only."
                )
            elif silence_stage == 2:
                await asyncio.sleep(10)
                if interview_ended:
                    return
                silence_stage = 3
                is_nudging = True
                print("🎙️ [SILENCE] Stage 2 -> 3 (End)")
                await session.generate_reply(
                    instructions="The candidate has not responded for a long time. End the session gracefully. Say exactly: 'It seems like we may have lost you — no worries at all. Our team will reach out to reschedule. Thanks for your time, goodbye!' Then immediately call the end_interview tool."
                )
        except asyncio.CancelledError:
            pass

    # =========================================================================
    # EVENT LISTENERS
    # =========================================================================

    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        state_str = str(ev.new_state).lower()
        if "speaking" in state_str and not agent_is_speaking:
            print("🎙️ [EVENT] User started speaking — cancelling silence timer.")
            cancel_pending_silence()
            cancel_silence_watcher()

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        nonlocal is_nudging, agent_is_speaking
        state_str = str(ev.new_state).lower()
        old_state_str = str(ev.old_state).lower()
        print(f"🤖 [EVENT] Agent state: {old_state_str} -> {state_str}")

        if "speaking" in state_str:
            # Agent speaking — cancel pending silence arm immediately.
            # Handles chunk-gap case: agent briefly touched "listening"
            # between streaming segments but is now continuing.
            agent_is_speaking = True
            cancel_pending_silence()
            cancel_silence_watcher()
            print("🔇 [ECHO] Echo window open — ignoring user VAD events")

        elif "listening" in state_str:
            # Agent finished a speech segment — start 2.5s pending delay
            # before arming the silence watcher. Also wait 600ms before
            # accepting user speech to let echo tail decay.
            async def _delayed_echo_close():
                await asyncio.sleep(0.6)
                nonlocal agent_is_speaking
                agent_is_speaking = False
                print("🎙️ [ECHO] Echo window closed — accepting user speech")

            asyncio.create_task(_delayed_echo_close())

            if is_nudging:
                is_nudging = False
                arm_silence_watcher_delayed(reset_stage=False)
            else:
                arm_silence_watcher_delayed(reset_stage=True)

        elif "thinking" in state_str:
            cancel_pending_silence()
            cancel_silence_watcher()

    # =========================================================================
    # START SESSION
    # =========================================================================

    await session.start(
        agent=interviewer_agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_L,
                    model_parameters=ai_coustics.ModelParameters(
                        enhancement_level=0.8,
                    ),
                    vad_settings=ai_coustics.VadSettings(
                        speech_hold_duration=0.3,
                        sensitivity=8.0,
                        minimum_speech_duration=0.0,
                    ),
                ),
            ),
        ),
    )

    await session.generate_reply(
        instructions=f"Begin the interview now. Your opening line is: {first_message}"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
    ))