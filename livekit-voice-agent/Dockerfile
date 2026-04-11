FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download Silero VAD model so prewarm() is instant at runtime
RUN python agent.py download-files

CMD ["python", "agent.py", "start"]