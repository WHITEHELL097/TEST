FROM python:3.11-slim

WORKDIR /app

# Install git and build tools
RUN apt-get update && apt-get install -y git build-essential ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Run bot
CMD ["python3", "main.py"]
