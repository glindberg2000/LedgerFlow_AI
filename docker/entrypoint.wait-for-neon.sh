#!/bin/sh
set -e
NEON_HOST="ep-floral-mode-aaxawm69-pooler.westus3.azure.neon.tech"

# Wait for DNS resolution
until getent hosts "$NEON_HOST"; do
  echo "Waiting for DNS for $NEON_HOST..."
  sleep 2
done

# Start Django
exec "$@" 