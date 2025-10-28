#!/bin/bash

# Setup PostgreSQL database for Django AssetTrack
echo "🐘 Setting up PostgreSQL database..."

# Install PostgreSQL
echo "📦 Installing PostgreSQL..."
sudo apt update
sudo apt install postgresql postgresql-contrib -y

# Start and enable PostgreSQL
echo "🔄 Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
echo "🗄️ Creating database and user..."
sudo -u postgres psql << 'EOF'
-- Create database
CREATE DATABASE assettrack;

-- Create user
CREATE USER assettrack_user WITH PASSWORD 'assettrack_password_2024';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE assettrack TO assettrack_user;

-- Connect to database and grant schema privileges
\c assettrack;
GRANT ALL ON SCHEMA public TO assettrack_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO assettrack_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO assettrack_user;

-- Exit
\q
EOF

# Install Python PostgreSQL adapter
echo "🐍 Installing PostgreSQL Python adapter..."
cd /var/www/assettrack
source venv/bin/activate
pip install psycopg2-binary

# Create .env file with database configuration
echo "📝 Creating environment configuration..."
sudo tee /var/www/assettrack/.env > /dev/null << 'EOF'
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=asset-track.harren-group.com,172.27.2.43,localhost

# Database Configuration
DATABASE_URL=postgresql://assettrack_user:assettrack_password_2024@localhost:5432/assettrack

# Azure AD Configuration (if needed)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
EOF

# Set proper permissions for .env file
sudo chown www-data:www-data /var/www/assettrack/.env
sudo chmod 600 /var/www/assettrack/.env

# Run migrations with new database
echo "🗄️ Running migrations with PostgreSQL..."
sudo -u www-data /var/www/assettrack/venv/bin/python manage.py migrate

# Create superuser
echo "👤 Creating superuser..."
sudo -u www-data /var/www/assettrack/venv/bin/python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()

# Create superuser
user = User.objects.create_superuser(
    username='admin',
    email='admin@harren-group.com',
    password='admin123'
)
print(f"✅ Superuser created: {user.username}")
EOF

# Collect static files
echo "📁 Collecting static files..."
sudo -u www-data /var/www/assettrack/venv/bin/python manage.py collectstatic --noinput

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart assettrack
sudo systemctl restart nginx

# Check status
echo "📊 Checking service status..."
sudo systemctl status assettrack --no-pager
sudo systemctl status postgresql --no-pager

echo "✅ PostgreSQL setup complete!"
echo "🌐 Test your application at: https://172.27.2.43/"
echo "🗄️ Database: PostgreSQL (much faster than SQLite)"
echo "👤 Login: admin / admin123"
