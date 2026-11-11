
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY . .

# Install project dependencies without installing the project itself
RUN uv sync --no-dev --no-install-project

# Start the Streamlit application
EXPOSE 8501

CMD ["uv", "run", "--no-sync", "--no-project", "streamlit", "run", "app.py", "--server.address=0.0.0.0"]
