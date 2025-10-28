#!/bin/bash

# Comprehensive diagnostic and fix for Django AssetTrack performance issues
echo "🔍 Diagnosing and fixing performance issues..."

# Navigate to project directory
cd /var/www/assettrack

# Check service status
echo "📊 Checking service status..."
echo "=== Django Service Status ==="
sudo systemctl status assettrack --no-pager -l

echo "=== Nginx Service Status ==="
sudo systemctl status nginx --no-pager -l

# Check if services are running
if ! sudo systemctl is-active --quiet assettrack; then
    echo "❌ Django service is not running!"
    echo "🔄 Starting Django service..."
    sudo systemctl start assettrack
fi

if ! sudo systemctl is-active --quiet nginx; then
    echo "❌ Nginx service is not running!"
    echo "🔄 Starting Nginx service..."
    sudo systemctl start nginx
fi

# Check database permissions
echo "📁 Checking database permissions..."
ls -la db.sqlite3
sudo chown www-data:www-data db.sqlite3
sudo chmod 664 db.sqlite3

# Activate virtual environment
source venv/bin/activate

# Run database migrations
echo "🗄️ Running database migrations..."
python3 manage.py migrate --noinput

# Collect static files properly
echo "📁 Collecting static files..."
sudo -u www-data /var/www/assettrack/venv/bin/python manage.py collectstatic --noinput --clear

# Fix all permissions
echo "📁 Fixing all permissions..."
sudo chown -R www-data:www-data /var/www/assettrack
sudo chmod -R 755 /var/www/assettrack
sudo chmod 664 /var/www/assettrack/db.sqlite3

# Check if static files exist
echo "📁 Checking static files..."
ls -la staticfiles/
ls -la staticfiles/admin/
ls -la staticfiles/css/

# Test Django directly
echo "🧪 Testing Django directly..."
timeout 10 python3 manage.py runserver 0.0.0.0:8001 &
DJANGO_PID=$!
sleep 5
if curl -s http://localhost:8001/ > /dev/null; then
    echo "✅ Django is working directly"
    kill $DJANGO_PID 2>/dev/null
else
    echo "❌ Django is not responding"
    kill $DJANGO_PID 2>/dev/null
fi

# Check Nginx configuration
echo "🔧 Checking Nginx configuration..."
sudo nginx -t

# Create optimized Nginx configuration
echo "🔧 Creating optimized Nginx configuration..."
sudo tee /etc/nginx/sites-available/assettrack > /dev/null << 'EOF'
# HTTP redirect to HTTPS
server {
    listen 80;
    server_name asset-track.harren-group.com 172.27.2.43;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration with performance optimizations
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
    
    # Static files with aggressive caching
    location /static/ {
        alias /var/www/assettrack/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        
        # Enable gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types text/css text/javascript application/javascript application/json;
        
        # Security
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Media files
    location /media/ {
        alias /var/www/assettrack/media/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # Main application with performance optimizations
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
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        
        # Keep-alive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Security: deny access to hidden files
    location ~ /\. {
        deny all;
    }
    
    # Enable gzip compression for all content
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
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
    
    # Wait for services to start
    sleep 3
    
    # Check final status
    echo "📊 Final service status..."
    sudo systemctl status assettrack --no-pager -l
    sudo systemctl status nginx --no-pager -l
    
    # Test application
    echo "🧪 Testing application..."
    if curl -s -k https://172.27.2.43/ > /dev/null; then
        echo "✅ Application is responding"
    else
        echo "❌ Application is not responding"
    fi
    
    echo "✅ Performance fixes complete!"
    echo "🌐 Test your application at: https://172.27.2.43/"
    echo "📁 Static files should now load properly"
else
    echo "❌ Nginx configuration test failed"
fi

# Show system resources
echo "📊 System resources:"
free -h
df -h
uptime
