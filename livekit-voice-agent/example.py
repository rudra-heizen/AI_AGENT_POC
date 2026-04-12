import os
from dotenv import load_dotenv
from livekit.agents import Agent, AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents import AgentSession
from livekit.plugins import openai, silero

load_dotenv()


def _normalize_azure_base_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/openai"):
        return endpoint
    return f"{endpoint}/openai"


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    openai_api_version = os.getenv("OPENAI_API_VERSION")


    llm_model = openai.realtime.RealtimeModel(
        voice="alloy",
        base_url=_normalize_azure_base_url(azure_endpoint), # type: ignore
        api_key=azure_api_key,
        azure_deployment=azure_deployment,
        api_version=openai_api_version,
    )

    session = AgentSession(
        vad=silero.VAD.load(),
        llm=llm_model
    )

    agent = Agent(
        instructions=(
            "You are an AI assistant conducting a structured technical interview. "
            "Ask your questions clearly, wait for the candidate to answer fully, "
            "and keep your responses concise."
        )
    )
    

    await session.start(agent=agent, room=ctx.room)
    
    # With Realtime-only setup (no standalone TTS), trigger the assistant to greet via LLM.
    session.generate_reply(
        instructions="Greet the candidate and ask if they are ready to begin."
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
