import os
from livekit import api
from dotenv import load_dotenv

load_dotenv()

# Generate a token that ONLY allows joining a specific room
token = api.AccessToken(
    os.getenv("LIVEKIT_API_KEY"),
    os.getenv("LIVEKIT_API_SECRET")
).with_identity("candidate_01").with_name("Candidate").with_grants(
    api.VideoGrants(room_join=True, room="interview-room")
).to_jwt()

print(f"URL: {os.getenv('LIVEKIT_URL')}")
print(f"TOKEN: {token}")