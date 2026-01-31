# Use an official lightweight Python image
FROM python:3.11-slim

# 1. Install System Dependencies & Node.js
# (Node is required because many MCP servers are NPM packages)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Install standard MCP Servers (Global Install)
# We install Brave Search (web) and Filesystem (writing reports)
RUN npm install -g @modelcontextprotocol/server-brave-search
RUN npm install -g @modelcontextprotocol/server-filesystem

# 5. Copy Source Code
COPY src/ ./src/

# 6. Expose the port (Cloud Run expects 8080 by default)
ENV PORT=8080
EXPOSE 8080

# 7. Start the FastAPI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]