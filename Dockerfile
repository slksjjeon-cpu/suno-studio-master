# Hugging Face Spaces Dockerfile for Suno Studio Master
FROM python:3.11-slim

# Prevent interactive prompts and configure python environment
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    HOST=0.0.0.0 \
    HOME=/home/user

# Install system dependencies (ffmpeg, libsndfile, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user with UID 1000 (standard for Hugging Face Spaces)
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

# Expose port 7860
EXPOSE 7860

# Start Suno Studio Master via Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
