# Audio Renderer Service - FluidSynth-based MIDI to WAV conversion
FROM python:3.11-slim

# Install FluidSynth and dependencies
RUN apt-get update && apt-get install -y \
    fluidsynth \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download FluidR3_GM soundfont
RUN mkdir -p /sf && \
    cd /sf && \
    wget -q https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create data directories
RUN mkdir -p /data/midi /data/audio /data/ambience

EXPOSE 9000

CMD ["python", "app.py"]
