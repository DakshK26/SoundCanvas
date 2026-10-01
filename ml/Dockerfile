# Builds the ml service image that serves /predict. It is built from inside ml/.
# Only what serving needs: the app, its two helpers and the trained model. No training scripts or data.
FROM python:3.12-slim

# Requirements are copied and installed before the code, so Docker can reuse the installed
# packages when only the code changes.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py dataset.py genres.py ./
COPY models/ models/

# Runs as an unprivileged user rather than root.
RUN useradd --system --no-create-home app
USER app
EXPOSE 5000
# uvicorn serves the FastAPI object called app in app.py.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
