#!/bin/bash

# Django AssetTrack Deployment Script for Linux Server
# Run this script on your Linux server to deploy the application

echo "🚀 Starting Django AssetTrack Deployment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib supervisor git

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /var/www/assettrack
sudo chown -R $USER:$USER /var/www/assettrack
cd /var/www/assettrack

# Clone repository (if not already present)
if [ ! -d ".git" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/Boateng555/assettrack-.git .
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > .env << EOF
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-server-ip,localhost
DATABASE_URL=postgresql://assettrack:your_password@localhost:5432/assettrack_db
EOF

# Set up PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE assettrack_db;"
sudo -u postgres psql -c "CREATE USER assettrack WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE assettrack_db TO assettrack;"

# Run Django migrations
echo "🔄 Running Django migrations..."
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 Creating superuser..."
echo "You can create a superuser later with: python manage.py createsuperuser"

echo "✅ Basic setup complete!"
echo "📋 Next steps:"
echo "1. Edit /var/www/assettrack/.env with your actual settings"
echo "2. Configure Nginx (see nginx.conf)"
echo "3. Configure systemd service (see assettrack.service)"
echo "4. Start services: sudo systemctl start assettrack && sudo systemctl enable assettrack"
echo "5. Restart Nginx: sudo systemctl restart nginx"
