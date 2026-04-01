FROM python:3.12-slim

# Install system dependencies needed to compile Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition first - Docker caches this layer
# so dependencies aren't reinstalled on every code change
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy the rest of the source code
COPY . .

RUN chmod +x start.sh

# Expose the port the app will run on
EXPOSE 8000

CMD ["bash", "start.sh"]
