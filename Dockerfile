FROM python:3.11.9-slim

# Install system dependencies (for moviepy, ffmpeg, etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Upgrade pip & install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]
