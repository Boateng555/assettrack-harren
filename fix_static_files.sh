#!/bin/bash

# Fix static files and performance issues for Django AssetTrack
echo "🔧 Fixing static files and performance..."

# Navigate to project directory
cd /var/www/assettrack

# Activate virtual environment
source venv/bin/activate

# Collect static files with proper permissions
echo "📁 Collecting static files..."
sudo -u www-data /var/www/assettrack/venv/bin/python manage.py collectstatic --noinput

# Fix static files permissions
echo "📁 Setting static files permissions..."
sudo chown -R www-data:www-data /var/www/assettrack/staticfiles
sudo chmod -R 755 /var/www/assettrack/staticfiles

# Fix database permissions
echo "📁 Setting database permissions..."
sudo chown www-data:www-data /var/www/assettrack/db.sqlite3
sudo chmod 664 /var/www/assettrack/db.sqlite3

# Fix project directory permissions
echo "📁 Setting project permissions..."
sudo chown -R www-data:www-data /var/www/assettrack
sudo chmod -R 755 /var/www/assettrack

# Update Nginx configuration for better static file serving
echo "🔧 Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/assettrack > /dev/null << 'EOF'
# HTTP redirect to HTTPS
server {
    listen 80;
    server_name asset-track.harren-group.com 172.27.2.43;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    server_name asset-track.harren-group.com 172.27.2.43;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/assettrack.crt;
    ssl_certificate_key /etc/ssl/private/assettrack.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Static files with proper caching and compression
    location /static/ {
        alias /var/www/assettrack/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        
        # Enable gzip compression for static files
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types text/css text/javascript application/javascript application/json;
    }
    
    # Media files
    location /media/ {
        alias /var/www/assettrack/media/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # Main application with optimizations
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Performance optimizations
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Security: deny access to hidden files
    location ~ /\. {
        deny all;
    }
    
    # Enable gzip compression for all content
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}
EOF

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    
    # Restart services
    echo "🔄 Restarting services..."
    sudo systemctl restart assettrack
    sudo systemctl restart nginx
    
    # Check service status
    echo "📊 Checking service status..."
    sudo systemctl status assettrack --no-pager -l
    sudo systemctl status nginx --no-pager -l
    
    echo "✅ Static files and performance fixes complete!"
    echo "🌐 Test your application at: https://172.27.2.43/"
    echo "📁 Static files should now load properly with CSS styling"
else
    echo "❌ Nginx configuration test failed"
    echo "Restoring backup configuration..."
    sudo cp /etc/nginx/sites-available/assettrack.backup /etc/nginx/sites-available/assettrack
    sudo systemctl restart nginx
fi
