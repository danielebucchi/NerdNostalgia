FROM python:3.13

# Install PostgreSQL client for pg_isready
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r src/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Copy and make entrypoint script executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
