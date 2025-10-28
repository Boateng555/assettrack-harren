#!/bin/bash

# Setup HTTPS for Django AssetTrack
echo "🔒 Setting up HTTPS for AssetTrack..."

# Create SSL certificate directory
sudo mkdir -p /etc/ssl/private /etc/ssl/certs

# Generate self-signed certificate
echo "📜 Generating SSL certificate..."
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/assettrack.key \
    -out /etc/ssl/certs/assettrack.crt \
    -subj "/C=US/ST=State/L=City/O=Harren Group/CN=asset-track.harren-group.com"

# Set proper permissions
sudo chmod 600 /etc/ssl/private/assettrack.key
sudo chmod 644 /etc/ssl/certs/assettrack.crt

# Backup current Nginx configuration
sudo cp /etc/nginx/sites-available/assettrack /etc/nginx/sites-available/assettrack.backup

# Copy new HTTPS configuration
sudo cp nginx_https.conf /etc/nginx/sites-available/assettrack

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    
    # Restart Nginx
    echo "🔄 Restarting Nginx..."
    sudo systemctl restart nginx
    
    # Check status
    echo "📊 Checking Nginx status..."
    sudo systemctl status nginx --no-pager
    
    echo "✅ HTTPS setup complete!"
    echo "🌐 Your application is now available at:"
    echo "   - https://asset-track.harren-group.com/"
    echo "   - https://172.27.2.43/"
    echo "   - HTTP will redirect to HTTPS"
    echo ""
    echo "⚠️  Note: Browsers will show a security warning for self-signed certificates."
    echo "   Click 'Advanced' and 'Proceed' to continue."
else
    echo "❌ Nginx configuration test failed"
    echo "Restoring backup configuration..."
    sudo cp /etc/nginx/sites-available/assettrack.backup /etc/nginx/sites-available/assettrack
    sudo systemctl restart nginx
fi
