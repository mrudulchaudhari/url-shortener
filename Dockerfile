FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python snipURL/manage.py collectstatic --noinput || true

# Change ownership
RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["gunicorn", "snipURL.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--chdir", "/app/snipURL"]
