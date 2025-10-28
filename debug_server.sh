#!/bin/bash

# Debug script to run Django in development mode
echo "🔍 Starting Django in debug mode to see errors..."

# Navigate to project directory
cd /var/www/assettrack

# Activate virtual environment
source venv/bin/activate

# Stop the systemd service
sudo systemctl stop assettrack

# Run Django in debug mode
echo "🚀 Starting Django development server..."
echo "Visit: http://172.27.2.43:8000"
echo "Press Ctrl+C to stop"

python manage.py runserver 0.0.0.0:8000
