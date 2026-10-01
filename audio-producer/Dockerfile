# Image for the audio-producer service; uvicorn serves the FastAPI app in app.py.
# fluidsynth and its General MIDI soundfont play the instruments; ffmpeg does the mastering.
FROM python:3.12-slim
# System tools: fluidsynth, the GM soundfont app.py's SOUNDFONT points at, ffmpeg for mixer.py,
# and libsndfile for the soundfile package. The apt cache is deleted to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fluidsynth fluid-soundfont-gm ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# Python packages first, so this layer stays cached when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Only the service modules; the tests aren't needed in the image.
COPY *.py .
# Run as an unprivileged user instead of root.
RUN useradd --system --no-create-home app
USER app
# Port 9001 is where the worker reaches the service (AUDIO_PRODUCER_URL).
EXPOSE 9001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9001"]
