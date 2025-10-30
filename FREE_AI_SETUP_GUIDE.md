# 🆓 Free AI Setup Guide for AssetTrack

## Overview
This guide shows you how to set up a **completely free, self-hosted AI assistant** for your AssetTrack application using Ollama. No API costs, no external dependencies, full privacy!

## 🎯 **Why Ollama?**
- ✅ **100% Free** - No API costs ever
- ✅ **Self-Hosted** - Runs on your Linux server
- ✅ **Privacy-First** - Data never leaves your server
- ✅ **Easy Setup** - Simple installation process
- ✅ **Multiple Models** - Choose from many free models
- ✅ **Django Integration** - Works perfectly with AssetTrack

## 🚀 **Quick Setup (Linux Server)**

### **Method 1: Automated Script (Recommended)**
```bash
# Make the script executable
chmod +x setup_ollama_linux.sh

# Run the setup script
./setup_ollama_linux.sh
```

### **Method 2: Manual Installation**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve &

# Download AI models
ollama pull llama3.2:3b
ollama pull tinyllama

# Test the setup
ollama run llama3.2:3b "Hello, are you working?"
```

### **Method 3: Docker (Easiest)**
```bash
# Start Ollama with Docker
docker run -d -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama

# Download models
docker exec -it <container_id> ollama pull llama3.2:3b
```

## 🔧 **Configuration**

### **1. Update Environment Variables**
Add to your `.env` file:
```env
# Ollama AI Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### **2. Update Django Settings**
The settings are already configured in `assettrack_django/settings.py`:
```python
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
```

### **3. Restart Your Application**
```bash
python manage.py runserver
```

## 🤖 **Available AI Models**

### **Recommended Models**

| Model | Size | RAM | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| **llama3.2:3b** | 3GB | 4GB | Fast | High | **Production servers** |
| **tinyllama** | 1GB | 2GB | Very Fast | Good | **Low-resource servers** |
| **phi3:mini** | 2GB | 3GB | Fast | High | **Balanced performance** |

### **Download Models**
```bash
# Download recommended model
ollama pull llama3.2:3b

# Download lightweight model
ollama pull tinyllama

# Download Microsoft model
ollama pull phi3:mini

# List all models
ollama list
```

## 🧪 **Testing the Setup**

### **1. Test Ollama API**
```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### **2. Test AssetTrack Integration**
```bash
# Run the test script
python setup_ai_models.py

# Test the AI assistant
python test_ai_assistant.py
```

### **3. Test in Browser**
1. Go to: `http://your-server:8000/ai-chat/`
2. Click the blue circle button
3. Ask: "Show me all laptops"

## 🐳 **Docker Deployment**

### **Complete Docker Setup**
```yaml
# docker-compose.ai.yml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped

  assettrack:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://ollama:11434
      - OLLAMA_MODEL=llama3.2:3b
    depends_on:
      - ollama
    restart: unless-stopped
```

### **Start with Docker**
```bash
# Start all services
docker-compose -f docker-compose.ai.yml up -d

# Download models
docker exec assettrack-ollama ollama pull llama3.2:3b

# Check status
docker-compose -f docker-compose.ai.yml ps
```

## 🔧 **System Requirements**

### **Minimum Requirements**
- **CPU**: 2 cores
- **RAM**: 4GB (for llama3.2:3b)
- **Storage**: 10GB free space
- **OS**: Linux (Ubuntu 20.04+, CentOS 7+, etc.)

### **Recommended Requirements**
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 20GB+ free space
- **OS**: Ubuntu 22.04 LTS

## 🚀 **Production Deployment**

### **1. Systemd Service**
```bash
# Create service file
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### **2. Nginx Configuration**
```nginx
# Add to your nginx.conf
location /ollama/ {
    proxy_pass http://localhost:11434/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### **3. Firewall Rules**
```bash
# Allow Ollama port
sudo ufw allow 11434

# Or if using iptables
sudo iptables -A INPUT -p tcp --dport 11434 -j ACCEPT
```

## 🔍 **Troubleshooting**

### **Common Issues**

1. **"Ollama not running"**
   ```bash
   # Check status
   systemctl status ollama
   
   # Start service
   sudo systemctl start ollama
   
   # Check logs
   journalctl -u ollama -f
   ```

2. **"Model not found"**
   ```bash
   # List models
   ollama list
   
   # Download model
   ollama pull llama3.2:3b
   ```

3. **"Connection refused"**
   ```bash
   # Check if Ollama is listening
   netstat -tlnp | grep 11434
   
   # Check firewall
   sudo ufw status
   ```

4. **"Out of memory"**
   ```bash
   # Use smaller model
   ollama pull tinyllama
   
   # Update .env
   OLLAMA_MODEL=tinyllama
   ```

### **Performance Optimization**

1. **Use SSD storage** for model files
2. **Allocate more RAM** to the Ollama process
3. **Use smaller models** for low-resource servers
4. **Enable GPU acceleration** (if available)

## 📊 **Monitoring**

### **Check Ollama Status**
```bash
# Service status
systemctl status ollama

# Process info
ps aux | grep ollama

# Memory usage
free -h

# Disk usage
df -h
```

### **Logs**
```bash
# Service logs
journalctl -u ollama -f

# Application logs
tail -f /var/log/assettrack/ai-assistant.log
```

## 🎉 **Success!**

Once set up, your AssetTrack application will have:

- **Free AI Assistant** - No API costs
- **Privacy Protection** - Data stays on your server
- **Smart Search** - Natural language queries
- **System Insights** - Real-time analytics
- **Context Awareness** - Knows what page you're on

### **Test Your Setup**
1. Go to: `http://your-server:8000/ai-chat/`
2. Ask: "Show me all laptops in Bremen"
3. Ask: "How many employees do we have?"
4. Ask: "What assets need maintenance?"

---

**🎊 Congratulations! You now have a completely free, self-hosted AI assistant! 🎊**
