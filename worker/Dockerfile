FROM python:3.12-slim

WORKDIR /app

# Copy backend requirements since the worker relies on backend models
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy worker code
COPY worker/ ./worker/

WORKDIR /app/worker

CMD ["python", "main.py"]
