# Only what serving needs: the app, its two helpers and the trained model. No training scripts or data.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py dataset.py genres.py ./
COPY models/ models/

RUN useradd --system --no-create-home app
USER app
EXPOSE 5000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
