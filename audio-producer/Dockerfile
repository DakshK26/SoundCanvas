# Audio Producer Service - Multi-stem rendering with mastering chain
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fluidsynth \
    ffmpeg \
    libsndfile1 \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app /sf /data/stems /data/midi /data/audio /data/patterns

# Download FluidR3_GM soundfont from alternative source
RUN wget --no-check-certificate -O /tmp/FluidR3_GM.zip \
    "https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.zip" \
    && cd /tmp \
    && unzip -q FluidR3_GM.zip \
    && mv FluidR3_GM.sf2 /sf/ \
    && rm FluidR3_GM.zip

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python modules
COPY app.py .
COPY mastering.py .
COPY stem_mixer.py .
COPY drum_sampler.py .
COPY fx_player.py .
COPY audio_validation.py .
COPY synth_drums.py .
COPY mix/ ./mix/
COPY assets/ ./assets/

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Run Flask app
CMD ["python", "app.py"]
