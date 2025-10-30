"""
AI Assistant for AssetTrack - Smart chatbot that understands the entire project
"""

import json
import requests
from django.conf import settings
from django.db.models import Q
from .models import Asset, Employee, Handover, WelcomePack
from datetime import datetime, timedelta

class AssetTrackAI:
    def __init__(self):
        # Initialize Ollama (free, self-hosted AI)
        self.ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
        self.model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
        
        # System prompt that teaches AI about AssetTrack
        self.system_prompt = """
        You are an AI assistant for AssetTrack, a comprehensive asset management system for Harren Group.
        
        SYSTEM CONTEXT:
        - Company: Harren Group (shipping and logistics)
        - Offices: Bremen Office, Hamburg Office, Other Locations
        - Asset types: Laptops, Phones, Monitors, Tablets, etc.
        - Employee management with departments and office locations
        - Handover system for asset transfers
        - Welcome pack system for new employees
        
        YOUR CAPABILITIES:
        1. Answer questions about assets (laptops, phones, etc.)
        2. Provide employee information and details
        3. Explain handover processes and status
        4. Help with welcome pack information
        5. Analyze asset health and maintenance needs
        6. Provide office-specific information
        7. Help with search and navigation
        8. Explain system features and processes
        
        RESPONSE STYLE:
        - Be helpful and professional
        - Provide specific, actionable information
        - Use bullet points for lists
        - Include relevant details (IDs, dates, status)
        - Suggest next steps when appropriate
        - Be concise but comprehensive
        """
    
    def get_context_data(self, current_page=None, user=None):
        """Get relevant context data based on current page and user"""
        context = {
            'current_page': current_page,
            'user': user.username if user else None,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Get basic statistics
        context['stats'] = {
            'total_assets': Asset.objects.count(),
            'total_employees': Employee.objects.count(),
            'total_handovers': Handover.objects.count(),
            'total_welcome_packs': WelcomePack.objects.count(),
        }
        
        # Get office distribution
        context['office_distribution'] = {
            'bremen_assets': Asset.objects.filter(office_location='bremen').count(),
            'hamburg_assets': Asset.objects.filter(office_location='hamburg').count(),
            'other_assets': Asset.objects.filter(office_location='other').count(),
        }
        
        # Get recent activity
        context['recent_activity'] = {
            'recent_handovers': list(Handover.objects.select_related('employee').order_by('-created_at')[:5].values(
                'id', 'employee__name', 'status', 'created_at'
            )),
            'recent_assets': list(Asset.objects.select_related('assigned_to').order_by('-created_at')[:5].values(
                'id', 'name', 'serial_number', 'asset_type', 'assigned_to__name'
            )),
        }
        
        return context
    
    def search_assets(self, query):
        """Search assets using natural language"""
        # Convert natural language to database queries
        assets = Asset.objects.filter(
            Q(name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(st_tag__icontains=query) |
            Q(model__icontains=query) |
            Q(manufacturer__icontains=query) |
            Q(assigned_to__name__icontains=query)
        )[:10]
        
        return list(assets.values(
            'id', 'name', 'serial_number', 'asset_type', 'status', 
            'office_location', 'assigned_to__name', 'health_score'
        ))
    
    def search_employees(self, query):
        """Search employees using natural language"""
        employees = Employee.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(department__icontains=query) |
            Q(phone__icontains=query)
        )[:10]
        
        return list(employees.values(
            'id', 'name', 'email', 'department', 'office_location', 'phone'
        ))
    
    def get_asset_details(self, asset_id):
        """Get detailed information about a specific asset"""
        try:
            asset = Asset.objects.select_related('assigned_to').get(id=asset_id)
            return {
                'id': str(asset.id),
                'name': asset.name,
                'serial_number': asset.serial_number,
                'st_tag': asset.st_tag,
                'asset_type': asset.asset_type,
                'model': asset.model,
                'manufacturer': asset.manufacturer,
                'status': asset.status,
                'office_location': asset.office_location,
                'assigned_to': asset.assigned_to.name if asset.assigned_to else None,
                'health_score': asset.health_score,
                'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else None,
                'created_at': asset.created_at.isoformat(),
            }
        except Asset.DoesNotExist:
            return None
    
    def get_employee_details(self, employee_id):
        """Get detailed information about a specific employee"""
        try:
            employee = Employee.objects.get(id=employee_id)
            return {
                'id': str(employee.id),
                'name': employee.name,
                'email': employee.email,
                'department': employee.department,
                'office_location': employee.office_location,
                'phone': employee.phone,
                'job_title': employee.job_title,
                'created_at': employee.created_at.isoformat(),
            }
        except Employee.DoesNotExist:
            return None
    
    def process_query(self, user_query, current_page=None, user=None):
        """Process user query and return AI response"""
        try:
            # Get context data
            context = self.get_context_data(current_page, user)
            
            # Search for relevant data
            assets = self.search_assets(user_query)
            employees = self.search_employees(user_query)
            
            # Prepare context for AI
            context['search_results'] = {
                'assets': assets,
                'employees': employees,
            }
            
            # Create user message with context
            user_message = f"""
            User Query: {user_query}
            
            Current Page: {current_page}
            User: {user.username if user else 'Anonymous'}
            
            Available Data:
            - Total Assets: {context['stats']['total_assets']}
            - Total Employees: {context['stats']['total_employees']}
            - Office Distribution: {context['office_distribution']}
            
            Search Results:
            - Found {len(assets)} assets matching query
            - Found {len(employees)} employees matching query
            
            Please provide a helpful response about the AssetTrack system, assets, employees, or any related information.
            """
            
            # Call Ollama API
            ollama_payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=ollama_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('message', {}).get('content', 'I apologize, but I could not generate a response.')
            else:
                ai_response = f"I apologize, but I encountered an error with the AI service (Status: {response.status_code}). Please try again."
            
            return {
                'response': ai_response,
                'context': context,
                'search_results': {
                    'assets': assets,
                    'employees': employees,
                }
            }
            
        except Exception as e:
            return {
                'response': f"I apologize, but I encountered an error: {str(e)}. Please try again or contact support.",
                'context': None,
                'search_results': {'assets': [], 'employees': []}
            }
    
    def get_quick_insights(self):
        """Get quick insights about the system"""
        insights = []
        
        # Asset health insights
        unhealthy_assets = Asset.objects.filter(health_score__lt=50).count()
        if unhealthy_assets > 0:
            insights.append(f"⚠️ {unhealthy_assets} assets need attention (health score < 50%)")
        
        # Pending handovers
        pending_handovers = Handover.objects.filter(status='Pending').count()
        if pending_handovers > 0:
            insights.append(f"📋 {pending_handovers} handovers are pending")
        
        # Unassigned assets
        unassigned_assets = Asset.objects.filter(assigned_to__isnull=True).count()
        if unassigned_assets > 0:
            insights.append(f"📦 {unassigned_assets} assets are unassigned")
        
        return insights
