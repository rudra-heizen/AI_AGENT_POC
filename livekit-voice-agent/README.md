# LiveKit Voice Interview Agent

This worker connects to the Next.js UI in `livekit-nextjs-voice-agent-interface`.

## What this does
- Registers as `inbound-agent`
- Receives dispatch from `app/api/connection-details/route.ts`
- Joins the same room as the browser user
- Runs a simple voice interview flow

## 1) Create and activate virtual env

```bash
cd /home/rpx/code/heizen/ai-agent-poc/livekit-voice-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure environment

```bash
cp .env.example .env
# edit .env with LiveKit + OpenAI keys
```

## 3) Run agent worker

```bash
python agent.py dev
```

Keep this running.

## 4) Run Next.js interface

In another terminal:

```bash
cd /home/rpx/code/heizen/ai-agent-poc/livekit-nextjs-voice-agent-interface
npm run dev
```

Open the app and click Start a conversation.

## Notes
- The UI dispatches an agent named `inbound-agent`.
- If you change agent name here, also update the API route in Next.js.
