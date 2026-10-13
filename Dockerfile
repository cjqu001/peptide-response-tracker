# Dockerfile - Habit tracker container for Synology NAS (Container Manager).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py serve.py ./
COPY templates ./templates

# Database is stored on a mounted volume so it survives container rebuilds.
ENV HABITS_DB=/data/habits.db
EXPOSE 5055

CMD ["python", "serve.py"]
