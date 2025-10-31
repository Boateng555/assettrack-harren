#!/bin/bash
# Fix Nginx timeout for AI chat endpoint
# Run this script on your server: sudo bash fix_nginx_ai_timeout.sh

set -e

echo "🔧 Fixing Nginx timeout configuration for AI chat endpoint..."

# Find the Nginx config file
CONFIG_FILE=$(grep -l "asset-track.harren-group.com" /etc/nginx/sites-available/* 2>/dev/null | head -1)

if [ -z "$CONFIG_FILE" ]; then
    echo "❌ Could not find Nginx config file"
    exit 1
fi

echo "📁 Found config file: $CONFIG_FILE"

# Backup the config
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"

# Remove ALL existing proxy timeout and buffering lines to avoid duplicates
echo "🧹 Cleaning up existing proxy settings..."
sed -i '/proxy_connect_timeout/d' "$CONFIG_FILE"
sed -i '/proxy_send_timeout/d' "$CONFIG_FILE"
sed -i '/proxy_read_timeout/d' "$CONFIG_FILE"
sed -i '/proxy_buffering/d' "$CONFIG_FILE"  # Remove ALL proxy_buffering lines (on, off, etc.)

# Find the proxy_pass line and add timeouts after it
if grep -q "proxy_pass http://127.0.0.1:8000" "$CONFIG_FILE"; then
    # Add timeouts after proxy_pass
    sed -i '/proxy_pass http:\/\/127.0.0.1:8000/a\        proxy_connect_timeout 30s;\n        proxy_send_timeout 120s;\n        proxy_read_timeout 120s;\n        proxy_buffering off;' "$CONFIG_FILE"
    echo "✅ Added timeout settings"
else
    echo "❌ Could not find proxy_pass line"
    exit 1
fi

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx config is valid"
    echo "🔄 Reloading Nginx..."
    systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
    echo ""
    echo "🎉 AI chat endpoint should now work without timeouts!"
    echo ""
    echo "Test with:"
    echo "curl -isk -H \"Content-Type: application/json\" \\"
    echo "  -X POST https://asset-track.harren-group.com/ai-chat/ \\"
    echo "  --data '{\"message\":\"Say hello\"}'"
else
    echo "❌ Nginx configuration test failed!"
    echo "Restoring backup..."
    cp "${CONFIG_FILE}.backup."* "$CONFIG_FILE" 2>/dev/null || true
    exit 1
fi

