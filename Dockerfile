# syntax=docker/dockerfile:1
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

FROM base as development

# Copy project files
COPY . .

# Command to run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base as production

# Set build-time environment variables
ARG SECRET_KEY
ARG DEBUG=0
ARG ALLOWED_HOSTS=localhost,127.0.0.1
ARG DATABASE_URL=postgres://ledgerflow:ledgerflow@postgres:5432/ledgerflow

# Set runtime environment variables
ENV SECRET_KEY=$SECRET_KEY \
    DEBUG=$DEBUG \
    ALLOWED_HOSTS=$ALLOWED_HOSTS \
    DATABASE_URL=$DATABASE_URL

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ledgerflow.wsgi:application"]