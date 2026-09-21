# Production Dockerfile for Content Creator Pipeline
# Includes Python 3.11, FFmpeg, and Playwright Chromium
FROM python:3.12.10

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (FFmpeg for video encoding, curl/ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright Chromium and required OS browser libraries
RUN playwright install --with-deps chromium

# Copy application source code
COPY . /app

# Ensure output directory exists
RUN mkdir -p /app/output

# Default Entrypoint & Command
ENTRYPOINT ["python"]
CMD ["run_pipeline.py", "--channel", "betheo"]
