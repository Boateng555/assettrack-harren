# 🐧 Linux Server Deployment Guide for Django AssetTrack

This guide will help you deploy your Django AssetTrack application on your Linux server.

## 📋 Prerequisites

- Ubuntu/Debian Linux server (root or sudo access)
- Domain name pointing to your server (optional but recommended)
- Basic knowledge of Linux commands

## 🚀 Quick Deployment

### Step 1: Upload Files to Server

```bash
# On your local machine, upload the project files
scp -r "C:\sal hardwear" user@your-server-ip:/home/user/
```

### Step 2: Run Deployment Script

```bash
# SSH into your server
ssh user@your-server-ip

# Make deployment script executable and run it
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Configure Services

```bash
# Copy Nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/assettrack
sudo ln -s /etc/nginx/sites-available/assettrack /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site

# Copy systemd service file
sudo cp assettrack.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/assettrack
sudo chown www-data:www-data /var/log/assettrack

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable assettrack
sudo systemctl start assettrack
sudo systemctl restart nginx
```

### Step 4: Configure Environment Variables

```bash
# Edit the environment file
sudo nano /var/www/assettrack/.env
```

Update these variables:
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-server-ip
DB_NAME=assettrack_db
DB_USER=assettrack
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

### Step 5: Create Superuser

```bash
cd /var/www/assettrack
source venv/bin/activate
python manage.py createsuperuser
```

## 🔧 Manual Configuration Steps

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib supervisor git
```

### 2. Set Up Database

```bash
sudo -u postgres psql
CREATE DATABASE assettrack_db;
CREATE USER assettrack WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE assettrack_db TO assettrack;
\q
```

### 3. Configure Django

```bash
cd /var/www/assettrack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Set Up SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 🔍 Troubleshooting

### Check Service Status

```bash
sudo systemctl status assettrack
sudo systemctl status nginx
sudo systemctl status postgresql
```

### View Logs

```bash
# Django application logs
sudo journalctl -u assettrack -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Django logs
sudo tail -f /var/log/assettrack/django.log
```

### Common Issues

1. **Permission Issues**: Make sure www-data owns the files
   ```bash
   sudo chown -R www-data:www-data /var/www/assettrack
   ```

2. **Database Connection**: Check PostgreSQL is running
   ```bash
   sudo systemctl status postgresql
   ```

3. **Static Files**: Recollect static files
   ```bash
   cd /var/www/assettrack
   source venv/bin/activate
   python manage.py collectstatic --noinput
   ```

## 🔒 Security Checklist

- [ ] Change default database password
- [ ] Set up firewall (ufw)
- [ ] Configure SSL certificate
- [ ] Set up regular backups
- [ ] Update system packages regularly
- [ ] Configure fail2ban for SSH protection

## 📊 Monitoring

### Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/assettrack
```

Add:
```
/var/log/assettrack/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

## 🚀 Your Application is Now Live!

Visit your server IP or domain to see your Django AssetTrack application running!

**Default URL**: `http://your-server-ip` or `http://your-domain.com`

## 📞 Support

If you encounter any issues:
1. Check the logs using the commands above
2. Verify all services are running
3. Check firewall settings
4. Ensure all environment variables are set correctly
