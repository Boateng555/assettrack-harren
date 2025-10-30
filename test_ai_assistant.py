#!/usr/bin/env python
"""
Test script for AI Assistant functionality
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

from assets.ai_assistant import AssetTrackAI
from assets.models import Asset, Employee
from django.contrib.auth.models import User

def test_ai_assistant():
    """Test AI Assistant functionality"""
    print("🤖 Testing AI Assistant...")
    
    try:
        # Initialize AI assistant
        ai = AssetTrackAI()
        print("✅ AI Assistant initialized")
        
        # Test context data
        print("📊 Testing context data...")
        context = ai.get_context_data('dashboard', User.objects.first())
        print(f"✅ Context data retrieved: {context['stats']}")
        
        # Test asset search
        print("🔍 Testing asset search...")
        assets = ai.search_assets('laptop')
        print(f"✅ Found {len(assets)} assets matching 'laptop'")
        
        # Test employee search
        print("👥 Testing employee search...")
        employees = ai.search_employees('admin')
        print(f"✅ Found {len(employees)} employees matching 'admin'")
        
        # Test quick insights
        print("💡 Testing quick insights...")
        insights = ai.get_quick_insights()
        print(f"✅ Generated {len(insights)} insights")
        for insight in insights:
            print(f"   - {insight}")
        
        # Test AI query processing (without actual API call)
        print("🧠 Testing query processing...")
        try:
            # This will fail without API key, but we can test the structure
            result = ai.process_query("Show me all laptops", "dashboard", User.objects.first())
            if result.get('response'):
                print("✅ Query processing successful")
            else:
                print("⚠️  Query processing failed (likely due to missing API key)")
        except Exception as e:
            print(f"⚠️  Query processing error (expected without API key): {e}")
        
        print()
        print("🎉 AI Assistant tests completed!")
        print()
        print("📋 Test Results Summary:")
        print(f"   - Assets in database: {Asset.objects.count()}")
        print(f"   - Employees in database: {Employee.objects.count()}")
        print(f"   - Assets found for 'laptop': {len(assets)}")
        print(f"   - Employees found for 'admin': {len(employees)}")
        print(f"   - Quick insights generated: {len(insights)}")
        print()
        print("💡 To test full AI functionality:")
        print("   1. Add your OpenAI API key to .env file")
        print("   2. Restart the Django server")
        print("   3. Try asking questions in the AI chat interface")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Assistant test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_ai_assistant()
