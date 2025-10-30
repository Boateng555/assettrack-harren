#!/bin/bash

# Ollama Setup Script for Linux Server
# This script installs Ollama and sets up a free AI model for AssetTrack

echo "🤖 Setting up Ollama (Free AI) for AssetTrack on Linux Server"
echo "=============================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Warning: Running as root. Consider running as a regular user."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "❌ Cannot detect Linux distribution"
    exit 1
fi

echo "📋 Detected OS: $OS $VER"

# Install Ollama
echo "📦 Installing Ollama..."

# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

if [ $? -eq 0 ]; then
    echo "✅ Ollama installed successfully"
else
    echo "❌ Failed to install Ollama"
    exit 1
fi

# Start Ollama service
echo "🚀 Starting Ollama service..."
ollama serve &

# Wait for Ollama to start
echo "⏳ Waiting for Ollama to start..."
sleep 10

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama failed to start"
    exit 1
fi

# Download recommended models
echo "📥 Downloading AI models..."

# Download Llama 3.2 3B (recommended for servers)
echo "   Downloading Llama 3.2 3B (3GB)..."
ollama pull llama3.2:3b

if [ $? -eq 0 ]; then
    echo "✅ Llama 3.2 3B downloaded successfully"
else
    echo "❌ Failed to download Llama 3.2 3B"
    exit 1
fi

# Download smaller model as backup
echo "   Downloading TinyLlama (1GB) as backup..."
ollama pull tinyllama

if [ $? -eq 0 ]; then
    echo "✅ TinyLlama downloaded successfully"
else
    echo "⚠️  TinyLlama download failed (optional)"
fi

# Test the model
echo "🧪 Testing AI model..."
TEST_RESPONSE=$(ollama run llama3.2:3b "Hello, are you working?" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ AI model is working correctly"
    echo "   Test response: ${TEST_RESPONSE:0:100}..."
else
    echo "❌ AI model test failed"
    exit 1
fi

# Create systemd service for Ollama
echo "🔧 Creating systemd service..."

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

# Create ollama user if it doesn't exist
if ! id "ollama" &>/dev/null; then
    sudo useradd -r -s /bin/false -m -d /usr/share/ollama ollama
fi

# Set up Ollama directory
sudo mkdir -p /usr/share/ollama/.ollama
sudo chown -R ollama:ollama /usr/share/ollama

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet ollama; then
    echo "✅ Ollama service is running"
else
    echo "❌ Ollama service failed to start"
    exit 1
fi

# Create environment file for AssetTrack
echo "📝 Creating environment configuration..."

cat > .env.ollama <<EOF
# Ollama AI Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Alternative models (uncomment to use):
# OLLAMA_MODEL=tinyllama
# OLLAMA_MODEL=llama3.2:1b
# OLLAMA_MODEL=phi3:mini
EOF

echo "✅ Environment file created: .env.ollama"

# Test the setup
echo "🧪 Testing complete setup..."

# Test API endpoint
API_TEST=$(curl -s -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }' 2>/dev/null)

if echo "$API_TEST" | grep -q "message"; then
    echo "✅ API endpoint is working"
else
    echo "❌ API endpoint test failed"
    exit 1
fi

# Show available models
echo "📋 Available AI models:"
ollama list

echo ""
echo "🎉 Ollama setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy the environment variables to your .env file:"
echo "   cat .env.ollama >> .env"
echo ""
echo "2. Restart your Django application:"
echo "   python manage.py runserver"
echo ""
echo "3. Test the AI Assistant:"
echo "   - Click the blue circle button in the app"
echo "   - Or go to: http://your-server:8000/ai-chat/"
echo ""
echo "🔧 Configuration:"
echo "   - Ollama URL: http://localhost:11434"
echo "   - Default Model: llama3.2:3b"
echo "   - Service: systemctl status ollama"
echo "   - Logs: journalctl -u ollama -f"
echo ""
echo "💡 Available models:"
echo "   - llama3.2:3b (recommended, 3GB)"
echo "   - tinyllama (lightweight, 1GB)"
echo "   - phi3:mini (Microsoft, 2GB)"
echo ""
echo "🆓 This is completely FREE and runs on your server!"
echo "   No API costs, no external dependencies, full privacy!"
