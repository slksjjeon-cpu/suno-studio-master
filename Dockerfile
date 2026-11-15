# Cloud Deployment Dockerfile for Suno Studio Master
FROM python:3.11-slim

# Prevent interactive prompts and configure python environment
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=10000 \
    HOST=0.0.0.0 \
    STUDIO_NO_BROWSER=1 \
    HOME=/home/user

# Install system dependencies (ffmpeg, libsndfile, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user with UID 1000
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

# Copy dependency specifications first for Docker layer caching
COPY --chown=user:user requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY --chown=user:user . .

# Ensure runtime directories exist and have proper permissions
RUN mkdir -p outputs uploads .hum_cache data

# Expose ports
EXPOSE 10000 7860 8000

# Start Suno Studio Master via Python launcher
CMD ["python", "app.py"]
