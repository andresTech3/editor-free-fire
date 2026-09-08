# CÓDIGO HEADSHOT STUDIO — DOCKERFILE FOR HUGGING FACE SPACES & CLOUD
FROM python:3.10-slim

# Install FFmpeg and system imaging dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR $HOME/app

# Install Python requirements
COPY --chown=user requirements_web.txt .
RUN pip install --no-cache-dir --user -r requirements_web.txt

# Copy project files
COPY --chown=user . $HOME/app

# Expose Hugging Face standard port
EXPOSE 7860

# Start server
CMD ["python", "web_server.py"]
