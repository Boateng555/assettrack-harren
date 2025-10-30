#!/usr/bin/env python
"""
Setup script for AI models in Ollama
"""

import requests
import time
import json
import subprocess
import sys

def check_ollama_running():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def wait_for_ollama():
    """Wait for Ollama to start"""
    print("⏳ Waiting for Ollama to start...")
    for i in range(30):  # Wait up to 30 seconds
        if check_ollama_running():
            print("✅ Ollama is running")
            return True
        print(f"   Attempt {i+1}/30...")
        time.sleep(1)
    return False

def download_model(model_name, description=""):
    """Download an AI model"""
    print(f"📥 Downloading {model_name} {description}...")
    
    try:
        # Use subprocess to call ollama pull
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {model_name} downloaded successfully")
            return True
        else:
            print(f"❌ Failed to download {model_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout downloading {model_name}")
        return False
    except Exception as e:
        print(f"❌ Error downloading {model_name}: {e}")
        return False

def test_model(model_name):
    """Test if a model is working"""
    print(f"🧪 Testing {model_name}...")
    
    try:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello, are you working?"}],
            "stream": False
        }
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result.get('message', {}).get('content', '')
            print(f"✅ {model_name} is working: {message[:50]}...")
            return True
        else:
            print(f"❌ {model_name} test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing {model_name}: {e}")
        return False

def list_models():
    """List available models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print("📋 Available models:")
            for model in models:
                name = model.get('name', 'Unknown')
                size = model.get('size', 0)
                size_gb = size / (1024**3)
                print(f"   - {name} ({size_gb:.1f}GB)")
            return models
        else:
            print("❌ Failed to list models")
            return []
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return []

def setup_ai_models():
    """Setup AI models for AssetTrack"""
    print("🤖 Setting up AI models for AssetTrack")
    print("=" * 50)
    
    # Check if Ollama is running
    if not check_ollama_running():
        print("❌ Ollama is not running. Please start Ollama first:")
        print("   ollama serve")
        print("   or run: ./setup_ollama_linux.sh")
        return False
    
    # List current models
    print("📋 Current models:")
    current_models = list_models()
    
    # Define models to download (in order of preference)
    models_to_download = [
        ("llama3.2:3b", "3GB - Recommended for servers"),
        ("tinyllama", "1GB - Lightweight backup"),
        ("phi3:mini", "2GB - Microsoft model"),
    ]
    
    print("\n📥 Downloading AI models...")
    
    successful_downloads = []
    
    for model_name, description in models_to_download:
        # Check if model already exists
        existing_models = [m.get('name', '') for m in current_models]
        if model_name in existing_models:
            print(f"✅ {model_name} already exists")
            successful_downloads.append(model_name)
            continue
        
        # Download the model
        if download_model(model_name, description):
            successful_downloads.append(model_name)
        else:
            print(f"⚠️  Skipping {model_name} due to download failure")
    
    print(f"\n✅ Successfully downloaded {len(successful_downloads)} models")
    
    # Test the primary model
    primary_model = "llama3.2:3b"
    if primary_model in successful_downloads:
        if test_model(primary_model):
            print(f"🎉 Primary model {primary_model} is working!")
        else:
            print(f"⚠️  Primary model {primary_model} test failed")
    else:
        print(f"⚠️  Primary model {primary_model} not available")
    
    # Show final status
    print("\n📋 Final model status:")
    list_models()
    
    print("\n🎉 AI model setup completed!")
    print("\n📋 Next steps:")
    print("1. Update your .env file with:")
    print("   OLLAMA_URL=http://localhost:11434")
    print("   OLLAMA_MODEL=llama3.2:3b")
    print()
    print("2. Restart your Django application:")
    print("   python manage.py runserver")
    print()
    print("3. Test the AI Assistant in your app!")
    print()
    print("💡 Model recommendations:")
    print("   - llama3.2:3b: Best quality, 3GB RAM")
    print("   - tinyllama: Fastest, 1GB RAM")
    print("   - phi3:mini: Good balance, 2GB RAM")
    
    return True

if __name__ == '__main__':
    setup_ai_models()
