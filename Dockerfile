FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install system dependencies (required for OpenCV and build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
COPY requirements_security.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements_security.txt \
    && pip install --no-cache-dir email-validator \
    && pip install --no-cache-dir gunicorn

# Copy the rest of the application
COPY . .

# Create directory for models and logs
RUN mkdir -p models/weights/skin_cancer \
    && mkdir -p models/weights/diabetic_retinopathy \
    && mkdir -p logs \
    && mkdir -p federated_data \
    && mkdir -p uploads

# Expose port
EXPOSE 8000

# Copy startup script (already copied via COPY . ., but explicit copy ensures location)
COPY scripts/download_more_models.py /app/scripts/
COPY scripts/download_additional_models.py /app/scripts/

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting Medora AI Server..."\n\
\n\
# Run database initialization if needed\n\
python3 scripts/check_and_seed_data.py || true\n\
\n\
# Download best models if they are missing (Self-healing)\n\
python3 scripts/download_more_models.py || true\n\
\n\
# Start the application with Gunicorn\n\
exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile -\n\
' > /app/startup.sh && chmod +x /app/startup.sh

# Start command
CMD ["/app/startup.sh"]
