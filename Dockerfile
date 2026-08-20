FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies (if PyMySQL/crypto needs compiling, though wheels usually suffice for 3.11)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure the uploads directory exists and is owned by the appuser
RUN mkdir -p uploads && chown -R appuser:appuser uploads /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 5000

# Gunicorn configuration via environment variables
# WEB_CONCURRENCY allows overriding the number of workers
ENV WEB_CONCURRENCY=2
ENV PORT=5000

# Start Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} app:app"]
