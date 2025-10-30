#!/usr/bin/env python
"""
Setup script for AI Assistant integration
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assettrack_django.settings')
django.setup()

from django.core.management import execute_from_command_line

def setup_ai_assistant():
    """Setup AI Assistant for AssetTrack"""
    print("🤖 Setting up AI Assistant for AssetTrack...")
    
    # Check if Ollama is running
    print("🔍 Checking Ollama service...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running")
        else:
            print("❌ Ollama is not responding")
            print("   Please start Ollama first:")
            print("   ollama serve")
            print("   or run: ./setup_ollama_linux.sh")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Please install and start Ollama first:")
        print("   curl -fsSL https://ollama.com/install.sh | sh")
        print("   ollama serve")
        return False
    
    # Check if models are available
    print("📋 Checking AI models...")
    try:
        models_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if models_response.status_code == 200:
            models = models_response.json().get('models', [])
            if models:
                print(f"✅ Found {len(models)} AI models:")
                for model in models:
                    print(f"   - {model.get('name', 'Unknown')}")
            else:
                print("⚠️  No AI models found. Downloading recommended model...")
                print("   Run: ollama pull llama3.2:3b")
        else:
            print("❌ Failed to check models")
    except Exception as e:
        print(f"❌ Error checking models: {e}")
    
    # Install required packages
    print("📦 Checking required packages...")
    try:
        import requests
        print("✅ requests package available")
    except ImportError:
        print("Installing requests package...")
        os.system("pip install requests>=2.32.0")
        print("✅ requests package installed")
    
    # Check Django setup
    print("🔍 Checking Django setup...")
    try:
        from assets.ai_assistant import AssetTrackAI
        print("✅ AI Assistant module imported successfully")
    except Exception as e:
        print(f"❌ Error importing AI Assistant: {e}")
        return False
    
    # Test AI Assistant initialization
    print("🧪 Testing AI Assistant initialization...")
    try:
        ai = AssetTrackAI()
        print("✅ AI Assistant initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing AI Assistant: {e}")
        print("   This might be due to missing OpenAI API key")
        return False
    
    # Test database connection
    print("🗄️  Testing database connection...")
    try:
        from assets.models import Asset, Employee
        asset_count = Asset.objects.count()
        employee_count = Employee.objects.count()
        print(f"✅ Database connected - {asset_count} assets, {employee_count} employees")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    print()
    print("🎉 AI Assistant setup completed!")
    print()
    print("📋 Next steps:")
    print("1. Add Ollama configuration to .env file:")
    print("   OLLAMA_URL=http://localhost:11434")
    print("   OLLAMA_MODEL=llama3.2:3b")
    print()
    print("2. Download AI models (if not already done):")
    print("   ollama pull llama3.2:3b")
    print("   ollama pull tinyllama")
    print()
    print("3. Restart your Django server:")
    print("   python manage.py runserver")
    print()
    print("4. Access the AI Assistant:")
    print("   - Click the blue circle button in bottom-right corner")
    print("   - Or go to: http://127.0.0.1:8000/ai-chat/")
    print("   - Or use the 'AI Assistant' link in the user menu")
    print()
    print("💡 Example questions to try:")
    print("   - 'Show me all laptops'")
    print("   - 'Find employees in Bremen'")
    print("   - 'What are the pending handovers?'")
    print("   - 'How many assets need maintenance?'")
    print("   - 'Tell me about the system'")
    print()
    print("🆓 This is completely FREE and runs on your server!")
    print("   No API costs, no external dependencies, full privacy!")
    
    return True

if __name__ == '__main__':
    setup_ai_assistant()
