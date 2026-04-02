FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for typical audio/video processing
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies file
COPY requirements.txt .

# Install python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the livekit agent
CMD ["python", "agent.py", "start"]
