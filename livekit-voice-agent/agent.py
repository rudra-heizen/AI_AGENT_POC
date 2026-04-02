import os
import time
from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, RunContext, cli, function_tool
from livekit.plugins import openai

load_dotenv()
from livekit.agents import WorkerOptions

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    # Record start time
    interview_start_time = time.time()

    # =========================================================================
    # 1. DEFINE TOOLS
    # =========================================================================
    @function_tool
    async def get_interview_question(context: RunContext, category: str, difficulty: str) -> str:
        """Fetch an interview question based on category and difficulty."""
        if category.lower() == "react":
            return "What is the Virtual DOM, and how does React use it to optimize performance?"
        else:
            return f"Can you explain a core concept regarding {category} and how you utilized it?"

    @function_tool
    async def check_time_remaining(context: RunContext) -> str:
        """Call this to check elapsed time. The target interview length is 8 to 10 minutes."""
        elapsed_seconds = time.time() - interview_start_time
        mins, secs = int(elapsed_seconds // 60), int(elapsed_seconds % 60)
        return f"{mins}m {secs}s elapsed."

    @function_tool
    async def end_interview(context: RunContext) -> str:
        """Call this function to end the interview. Use ONLY after you have said your final goodbye."""
        import asyncio
        await asyncio.sleep(2) # Buffer for final audio to play
        await ctx.room.disconnect()
        return "Disconnected"

    # =========================================================================
    # 2. THE AUTONOMOUS PROMPT
    # =========================================================================
    AUTONOMOUS_PROMPT = """
    You are Alex, an experienced technical interviewer at Heizen, conducting a Round 1 screening voice interview for the SDE Intern position.
    ## About Heizen & The Role
    Heizen is an AI-powered software services startup founded by elite alumni. We combine top engineering talent with proprietary AI agents to build enterprise-grade products. You are interviewing candidates for the SDE Intern role.

    ## TIME MANAGEMENT & TOOL USAGE (CRITICAL)
    Total Interview Duration: 8 to 10 minutes. You are strictly responsible for managing the pace.
    You have access to three tools: `check_time_remaining`, `get_interview_question`, and `end_interview`.

    *   **Phase 1: Intro & Background (Mins 0-3)**
        *   Goal: Understand their background and their best work. 
        *   Action: Ask about a specific project. Dig deeply into their role, the challenges they faced, and the tech stack. For example, if they mention building a review aggregation platform, ask how they integrated various third-party APIs or managed data consistency in MySQL.
        *   *Tool Check:* Call `check_time_remaining` to ensure you transition around the 3-minute mark.
    *   **Phase 2: Technical Questions (Mins 3-8)**
        *   Goal: Assess technical knowledge based strictly on their background. 
        *   Action: Call the `get_interview_question` tool using a category the candidate explicitly mentioned (e.g., Java, React, Database Optimization).
        *   *Tool Check:* Call `check_time_remaining` periodically. Around the 8-minute mark, transition to Phase 3.
    *   **Phase 3: Wrap-up (Mins 8-10)**
        *   Goal: Conclude the interview professionally.
        *   Action: Ask if they have any questions about Heizen. Thank them for their time and explain that the team will reach out in a few days. 
        *   *Tool Check:* After saying your final goodbye, you MUST call the `end_interview` tool to disconnect the call.

    ## CORE CONDUCT RULES FOR VOICE INTERVIEWS
    1.  **ONE QUESTION AT A TIME (NON-NEGOTIABLE):** Never stack multiple questions in a single breath. Ask ONE short, focused question and STOP talking. Wait for their answer.
        *   *Bad:* "Can you explain how indexing works? Also, what are the drawbacks?"
        *   *Good:* "Can you explain how indexing works in a database?" [Wait for answer].
    2.  **CONVERSATIONAL & CONCISE:** Keep all responses to 2-3 sentences maximum. Sound like a friendly human colleague, not a robot reading a rubric. Do not read code out loud.
    3.  **COMPLETE THE THOUGHT:** Do not move to the next question until the candidate has given a satisfactory answer or admitted they don't know. If their answer is vague, probe for depth. If they mention optimizing a function, ask about their approach to time complexity.
    4.  **CONTEXT-AWARE ONLY:** Never ask about technologies they haven't mentioned. If they only know Python, do not ask about JavaScript.
    5.  **SMOOTH TRANSITIONS:** Acknowledge their previous answer briefly before pivoting. ("That makes sense. Moving on to another area you mentioned...")
    6.  **EARLY TERMINATION:** If the candidate explicitly asks to stop, end, pause, or abort the interview at ANY time, respect their request immediately. Say a polite, brief goodbye (e.g., "Understood, we'll stop here. Have a great day!"), and immediately call the end_interview tool. Do NOT attempt to complete the remaining phases or ask wrap-up questions.
    Match the candidate's energy, be encouraging if they are nervous, and focus on understanding their problem-solving mindset.
    """

    model = openai.realtime.RealtimeModel.with_azure(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION")
    )

    interviewer_agent = Agent(
        instructions=AUTONOMOUS_PROMPT,
        tools=[get_interview_question, check_time_remaining, end_interview] 
    )
    
    session = AgentSession(llm=model)
    await session.start(agent=interviewer_agent, room=ctx.room)

    # =========================================================================
    # 3. KICK OFF
    # =========================================================================
    await session.generate_reply(
        instructions="""Kick off the interview warmly. Say exactly: 'Hi there, I'm Alex from Heizen. It's great to meet you! To get us started, could you give me a brief introduction.'"""
    )

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="inbound-agent"
        )
    )