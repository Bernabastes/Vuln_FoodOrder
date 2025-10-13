#!/bin/bash

# Production startup script for Render deployment

# Set environment variables
export PYTHONPATH=/opt/render/project/src
export FLASK_APP=app.py
export FLASK_ENV=production

# Create uploads directory if it doesn't exist
mkdir -p /app/uploads

# Initialize database if needed
if [ ! -f "/app/vulneats.db" ] && [ -z "$DATABASE_URL" ]; then
    echo "Initializing SQLite database..."
    python init_db.py
fi

# Start the Flask application
echo "Starting Flask application..."
python app.py
