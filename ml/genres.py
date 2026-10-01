"""The four genres. train.py, app.py, dataset.py and evaluate.ipynb import this list.
The index is the model's output index, so reordering this breaks the saved model.
The names must match the other services (GENRES in api/src/schema.ts, cpp-core/src/GenreTemplate.cpp,
KITS in audio-producer/drums.py and MIXES in audio-producer/mixer.py); ml/tests checks this."""
GENRES = ["EDM_CHILL", "EDM_DROP", "CINEMATIC", "HOUSE"]
