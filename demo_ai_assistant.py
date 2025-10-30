#!/usr/bin/env python
"""
Demo script showing AI Assistant capabilities
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

def demo_ai_assistant():
    """Demo AI Assistant capabilities"""
    print("🤖 AI Assistant Demo for AssetTrack")
    print("=" * 50)
    
    try:
        # Initialize AI assistant
        ai = AssetTrackAI()
        print("✅ AI Assistant initialized successfully")
        print()
        
        # Get system statistics
        print("📊 System Statistics:")
        context = ai.get_context_data('dashboard', User.objects.first())
        stats = context['stats']
        print(f"   - Total Assets: {stats['total_assets']}")
        print(f"   - Total Employees: {stats['total_employees']}")
        print(f"   - Total Handovers: {stats['total_handovers']}")
        print(f"   - Total Welcome Packs: {stats['total_welcome_packs']}")
        print()
        
        # Office distribution
        print("🏢 Office Distribution:")
        office_dist = context['office_distribution']
        print(f"   - Bremen Office: {office_dist['bremen_assets']} assets")
        print(f"   - Hamburg Office: {office_dist['hamburg_assets']} assets")
        print(f"   - Other Locations: {office_dist['other_assets']} assets")
        print()
        
        # Quick insights
        print("💡 Quick Insights:")
        insights = ai.get_quick_insights()
        for insight in insights:
            print(f"   - {insight}")
        print()
        
        # Demo searches
        print("🔍 Search Demonstrations:")
        
        # Search for laptops
        print("   Searching for 'laptop'...")
        laptops = ai.search_assets('laptop')
        print(f"   Found {len(laptops)} laptops:")
        for laptop in laptops[:3]:  # Show first 3
            print(f"     - {laptop['name']} ({laptop['serial_number']}) - {laptop['asset_type']}")
        if len(laptops) > 3:
            print(f"     ... and {len(laptops) - 3} more")
        print()
        
        # Search for employees
        print("   Searching for 'admin'...")
        admins = ai.search_employees('admin')
        print(f"   Found {len(admins)} employees:")
        for admin in admins[:3]:  # Show first 3
            print(f"     - {admin['name']} - {admin['department']}")
        if len(admins) > 3:
            print(f"     ... and {len(admins) - 3} more")
        print()
        
        # Search for Bremen employees
        print("   Searching for 'Bremen' employees...")
        bremen_employees = ai.search_employees('Bremen')
        print(f"   Found {len(bremen_employees)} Bremen employees:")
        for emp in bremen_employees[:3]:  # Show first 3
            print(f"     - {emp['name']} - {emp['department']}")
        if len(bremen_employees) > 3:
            print(f"     ... and {len(bremen_employees) - 3} more")
        print()
        
        # Show recent activity
        print("📈 Recent Activity:")
        recent_activity = context['recent_activity']
        print("   Recent Handovers:")
        for handover in recent_activity['recent_handovers'][:3]:
            created_at = handover['created_at']
            if hasattr(created_at, 'strftime'):
                date_str = created_at.strftime('%Y-%m-%d')
            else:
                date_str = str(created_at)[:10]
            print(f"     - {handover['employee__name']} - {handover['status']} ({date_str})")
        print()
        print("   Recent Assets:")
        for asset in recent_activity['recent_assets'][:3]:
            print(f"     - {asset['name']} ({asset['serial_number']}) - {asset['asset_type']}")
        print()
        
        # Demo AI queries (without API key)
        print("🧠 AI Query Examples:")
        print("   The AI Assistant can answer questions like:")
        print("   - 'Show me all laptops in Bremen office'")
        print("   - 'Find employees with pending handovers'")
        print("   - 'What assets need maintenance?'")
        print("   - 'How many unassigned assets do we have?'")
        print("   - 'Tell me about the system status'")
        print()
        
        print("🎉 Demo completed successfully!")
        print()
        print("📋 To use the AI Assistant:")
        print("   1. Add your OpenAI API key to .env file")
        print("   2. Restart the Django server")
        print("   3. Click the blue circle button in the bottom-right corner")
        print("   4. Or go to: http://127.0.0.1:8000/ai-chat/")
        print("   5. Start asking questions!")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    demo_ai_assistant()
