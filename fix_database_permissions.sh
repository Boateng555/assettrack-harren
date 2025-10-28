#!/bin/bash

# Fix database permissions for Django AssetTrack
echo "🔧 Fixing database permissions..."

# Navigate to project directory
cd /var/www/assettrack

# Fix database file permissions
echo "📁 Setting database permissions..."
sudo chown www-data:www-data db.sqlite3
sudo chmod 664 db.sqlite3

# Fix directory permissions
echo "📁 Setting directory permissions..."
sudo chown -R www-data:www-data /var/www/assettrack
sudo chmod -R 755 /var/www/assettrack

# Fix specific database directory
sudo chmod 755 /var/www/assettrack
sudo chmod 664 /var/www/assettrack/db.sqlite3

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart assettrack
sudo systemctl restart nginx

# Check database permissions
echo "📊 Checking database permissions..."
ls -la db.sqlite3

echo "✅ Database permissions fixed!"
echo "🌐 Test your application at: https://172.27.2.43/"
