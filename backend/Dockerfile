FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including git for repository cloning)
RUN apt-get update && apt-get install -y libpq-dev gcc git curl && rm -rf /var/lib/apt/lists/*

# Install pip dependencies
COPY pyproject.toml ./
RUN pip install .

COPY src/ ./src/

CMD ["python", "-m", "src.main"]
