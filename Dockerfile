FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Expose port for web interface
EXPOSE 5002

# Run the application
CMD ["python", "app.py"]