"""
Production settings for assettrack_django project.
For Windows Server deployment.
"""

from .settings import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Get the server's IP address - you'll need to replace this with your actual server IP
SERVER_IP = os.getenv('SERVER_IP', '0.0.0.0')  # Replace with your actual server IP
SERVER_DOMAIN = os.getenv('SERVER_DOMAIN', 'your-domain.com')  # Replace with your domain if you have one

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'asset-track.harren-group.com',
    '172.27.2.43',
    SERVER_IP,
    SERVER_DOMAIN,
    # Add your server's actual IP address here
    # Example: '192.168.1.100', '10.0.0.50'
]

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = [
    f'http://{SERVER_IP}',
    f'https://{SERVER_IP}',
    f'http://{SERVER_DOMAIN}',
    f'https://{SERVER_DOMAIN}',
    'http://asset-track.harren-group.com',
    'https://asset-track.harren-group.com',
    'http://172.27.2.43',
    'https://172.27.2.43',
]

# Static files configuration for production
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session security
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
CSRF_COOKIE_SECURE = False     # Set to True if using HTTPS

# Database configuration for production (you might want to use SQL Server or PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
