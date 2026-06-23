FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies for pdf/images parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./api ./api
COPY ./agents ./agents
COPY ./tools ./tools
COPY ./memory ./memory
COPY ./workflows ./workflows
COPY ./database ./database
COPY ./mcp ./mcp
COPY ./prompts ./prompts
COPY ./frontend ./frontend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

