# Use python 3.10-slim to match our project version
FROM python:3.10-slim

# Ensure Python logs are streamed to stdout/stderr immediately
ENV PYTHONUNBUFFERED=1

# 1. Install Chrome, ChromeDriver, and system dependencies
# We include curl/wget/gnupg just in case, and build-essential for some python packages
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy requirements first to leverage Docker cache
COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application
COPY . .

# 6. Set Environment Variables for Selenium
# These point to the binaries we just installed via apt-get
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 7. Copy and executable permission for entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 8. Expose port for Railway internal networking
EXPOSE 8000

# 9. Run the entrypoint script
CMD ["./entrypoint.sh"]
