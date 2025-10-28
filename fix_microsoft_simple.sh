#!/bin/bash

# Simple fix for Microsoft provider
echo "🔧 Fixing Microsoft provider..."

# Navigate to project directory
cd /var/www/assettrack

# Activate virtual environment
source venv/bin/activate

# Create Microsoft social app in database
python manage.py shell << 'EOF'
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

# Get or create the site
site, created = Site.objects.get_or_create(
    domain='172.27.2.43',
    defaults={'name': 'AssetTrack'}
)

# Create or update Microsoft social app
microsoft_app, created = SocialApp.objects.get_or_create(
    provider='microsoft',
    defaults={
        'name': 'Microsoft',
        'client_id': 'your-client-id',
        'secret': 'your-client-secret',
    }
)

# Add the site to the social app
microsoft_app.sites.add(site)

print(f"✅ Microsoft social app {'created' if created else 'updated'}")
print(f"✅ Site: {site.domain}")
EOF

# Restart services
sudo systemctl restart assettrack
sudo systemctl restart nginx

echo "✅ Microsoft provider fix complete!"
echo "🌐 Test your application at: http://172.27.2.43"
