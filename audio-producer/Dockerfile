# Audio Producer Service - Multi-stem rendering with mastering chain
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fluidsynth \
    ffmpeg \
    libsndfile1 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app /sf /data/stems /data/midi /data/audio /data/patterns

# Download FluidR3_GM soundfont (with fallback URLs)
RUN (wget -q https://keymusician.com/FluidR3_GM.zip -O /tmp/FluidR3_GM.zip || \
     wget -q https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2 -O /sf/FluidR3_GM.sf2) \
    && if [ -f /tmp/FluidR3_GM.zip ]; then \
         cd /tmp && unzip -q FluidR3_GM.zip && mv FluidR3_GM.sf2 /sf/ && rm FluidR3_GM.zip; \
       fi || echo "SoundFont download failed, will need manual installation"

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY mix ./mix
COPY assets ./assets

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Run Flask app
CMD ["python", "app.py"]
