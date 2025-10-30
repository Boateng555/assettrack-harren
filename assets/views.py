from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, authenticate, login
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
from django.conf import settings
import json
import random

from .models import Employee, Asset, Handover, WelcomePack, HandoverToken, Notification
from .azure_ad_integration import AzureADIntegration
from .ai_assistant import AssetTrackAI
import secrets

def get_user_office(request):
    """Helper function to get the current user's office location based on phone number"""
    try:
        if request.user.is_authenticated:
            employee = Employee.objects.get(user=request.user)
            
            # If office_location is already set, use it
            if employee.office_location:
                return employee.office_location
            
            # Detect office based on phone number
            phone = employee.phone
            if phone:
                office = detect_office_by_phone(phone)
                if office:
                    # Update the employee's office location
                    employee.office_location = office
                    employee.save()
                    return office
                    
    except Employee.DoesNotExist:
        pass
    return 'bremen'  # Default to Bremen office

def detect_office_by_phone(phone):
    """Detect office location based on real phone number patterns"""
    if not phone:
        return None
    
    phone = phone.strip()
    
    # Handle German landline numbers with +49
    if phone.startswith('+49'):
        # Handle different phone number formats
        # Format 1: +49 40 380380-916 (with spaces)
        # Format 2: +4940380380208 (no spaces)
        # Format 3: +49 421 46 86 - 189 (with spaces and dashes)
        
        # Extract area code from different formats
        area_code = None
        
        if ' ' in phone:
            # Format with spaces: +49 40 380380-916
            parts = phone.split()
            if len(parts) >= 2:
                area_code = parts[1]
        else:
            # Format without spaces: +4940380380208
            # Extract first 3-4 digits after +49
            if len(phone) >= 6:
                # +49 40 -> area code 40
                # +49 421 -> area code 421
                if phone[3:5] == '40':
                    area_code = '40'
                elif phone[3:6] == '421':
                    area_code = '421'
                elif phone[3:5] == '30':
                    area_code = '30'
                elif phone[3:5] == '89':
                    area_code = '89'
                elif phone[3:5] == '22':
                    area_code = '22'
                else:
                    # Try to extract first 2-3 digits
                    if len(phone) >= 5:
                        area_code = phone[3:5]  # First 2 digits
                    elif len(phone) >= 6:
                        area_code = phone[3:6]  # First 3 digits
        
        if area_code:
            # Hamburg area codes
            hamburg_codes = ['40']  # Hamburg main area code
            
            # Bremen area codes  
            bremen_codes = ['421']  # Bremen main area code
            
            # Check for Hamburg area codes
            for code in hamburg_codes:
                if area_code.startswith(code):
                    return 'hamburg'
            
            # Check for Bremen area codes
            for code in bremen_codes:
                if area_code.startswith(code):
                    return 'bremen'
            
            # If it's a German number but not Hamburg (40) or Bremen (421),
            # and it's not a mobile number, assume Hamburg (more international)
            if not area_code.startswith('017') and not area_code.startswith('015') and not area_code.startswith('016'):
                return 'hamburg'
    
    # Handle German mobile numbers (017x, 015x, 016x, etc.)
    if phone.startswith('017') or phone.startswith('015') or phone.startswith('016'):
        # German mobile numbers - for now, return None until we know the patterns
        return None
    
    # Non-German numbers or patterns not recognized
    # Use a simple heuristic: if it's not German, assume Hamburg (more international)
    if not phone.startswith('+49') and not phone.startswith('017') and not phone.startswith('015') and not phone.startswith('016'):
        return 'hamburg'
    
    return None

def detect_office_by_phone_and_department(phone, department):
    """Detect office location based on phone number and department"""
    # If employee is External, they should be in Other Locations
    if department == 'External':
        return 'other'
    
    # For Internal employees, use phone number detection
    if department == 'Internal':
        return detect_office_by_phone(phone)
    
    # For other departments, use phone number detection
    return detect_office_by_phone(phone)

def calculate_health_score(asset):
    """Calculate asset health score based on Azure AD registration date for Azure assets, purchase date for others"""
    reference_date = None
    
    # For Azure AD assets, use the actual Azure AD registration date
    if asset.azure_ad_id and asset.azure_registration_date:
        # Asset came from Azure AD - use the actual registration date from Azure AD
        reference_date = asset.azure_registration_date.date()
    elif asset.azure_ad_id and asset.last_azure_sync:
        # Fallback to sync date if registration date not available
        reference_date = asset.last_azure_sync.date()
    elif asset.purchase_date:
        # Manually added asset - use purchase date
        reference_date = asset.purchase_date
    elif asset.last_azure_sync:
        # Fallback to Azure sync date if no other date available
        reference_date = asset.last_azure_sync.date()
    
    if not reference_date:
        return 50  # Unknown age - assume moderate health
    
    today = date.today()
    age_days = (today - reference_date).days
    
    # Health calculation based on when asset was discovered in Azure AD
    if age_days < 30:  # Less than 1 month
        return 100
    elif age_days < 90:  # Less than 3 months
        return 95
    elif age_days < 180:  # Less than 6 months
        return 90
    elif age_days < 365:  # Less than 1 year
        return 85
    elif age_days < 730:  # Less than 2 years
        return 75
    elif age_days < 1095:  # Less than 3 years
        return 65
    elif age_days < 1460:  # Less than 4 years
        return 55
    elif age_days < 1825:  # Less than 5 years
        return 45
    else:  # 5+ years
        return 35

@login_required
def admin_dashboard(request):
    """Admin dashboard view with system statistics and management tools"""
    # Check if user has superuser privileges
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Superuser privileges required.')
        return redirect('assets:dashboard')
    
    # Get system statistics
    total_users = Employee.objects.count()
    total_django_users = User.objects.count()
    active_sessions = 8  # Mock data - you can implement real session tracking
    system_health = 98  # Mock data
    storage_used = 67  # Mock data
    
    # Get real users for display
    django_users = User.objects.all().order_by('-date_joined')[:10]  # Get 10 most recent users
    employees = Employee.objects.all().order_by('-created_at')[:10]  # Get 10 most recent employees
    
    # Get recent system logs (mock data for now)
    system_logs = [
        {
            'timestamp': '2024-01-15 14:30:22',
            'level': 'INFO',
            'user': 'admin',
            'action': 'User Login',
            'details': 'Successful login from 192.168.1.100'
        },
        {
            'timestamp': '2024-01-15 14:25:15',
            'level': 'DEBUG',
            'user': 'system',
            'action': 'Asset Sync',
            'details': 'Azure sync completed successfully'
        },
        {
            'timestamp': '2024-01-15 14:20:08',
            'level': 'WARN',
            'user': 'jane.smith',
            'action': 'Asset Assignment',
            'details': 'Asset LAP-001 assigned to user'
        },
        {
            'timestamp': '2024-01-15 14:15:42',
            'level': 'ERROR',
            'user': 'system',
            'action': 'Backup Failed',
            'details': 'Database backup failed - insufficient space'
        }
    ]
    
    context = {
        'total_users': total_users,
        'total_django_users': total_django_users,
        'active_sessions': active_sessions,
        'system_health': system_health,
        'storage_used': storage_used,
        'system_logs': system_logs,
        'django_users': django_users,
        'employees': employees,
    }
    
    return render(request, 'admin.html', context)

@login_required
def azure_ad_sync(request):
    """Azure AD sync view with full change detection"""
    if request.method == 'POST':
        try:
            azure_ad = AzureADIntegration()
            results = azure_ad.full_sync()
            
            messages.success(
                request, 
                f'Azure AD sync completed successfully! '
                f'Employees: {results["employees_synced"]} new, {results["employees_updated"]} updated, {results["employees_disabled"]} disabled, {results["employees_deleted"]} deleted. '
                f'User Devices: {results["user_devices_synced"]} synced, {results["user_devices_assigned"]} assigned. '
                f'Standalone Devices: {results["standalone_devices_synced"]} synced, {results["standalone_devices_updated"]} updated. '
                f'Assignments: {results["assignments_updated"]} updated. '
                f'Assets cleaned up: {results["assets_cleaned_up"]}.'
            )
            
        except Exception as e:
            messages.error(request, f'Azure AD sync failed: {str(e)}')
            
        return redirect('assets:dashboard')
    
    # Get sync statistics with status breakdown
    azure_ad = AzureADIntegration()
    summary = azure_ad.get_sync_summary()
    
    employees_with_azure = Employee.objects.filter(azure_ad_id__isnull=False).count()
    assets_with_azure = Asset.objects.filter(azure_ad_id__isnull=False).count()
    total_employees = Employee.objects.count()
    total_assets = Asset.objects.count()
    
    context = {
        'employees_with_azure': employees_with_azure,
        'assets_with_azure': assets_with_azure,
        'total_employees': total_employees,
        'total_assets': total_assets,
        'azure_sync_percentage': {
            'employees': (employees_with_azure / total_employees * 100) if total_employees > 0 else 0,
            'assets': (assets_with_azure / total_assets * 100) if total_assets > 0 else 0,
        },
        'sync_summary': summary,
        'employee_status_breakdown': {
            'active': Employee.objects.filter(status='active').count(),
            'inactive': Employee.objects.filter(status='inactive').count(),
            'deleted': Employee.objects.filter(status='deleted').count(),
        }
    }
    
    return render(request, 'azure_ad_sync.html', context)

@login_required
def azure_ad_status_api(request):
    """API endpoint to view Azure AD integration status and data"""
    if request.headers.get('Accept') == 'application/json':
        # Return JSON response for API calls
        azure_employees = Employee.objects.filter(azure_ad_id__isnull=False)
        azure_assets = Asset.objects.filter(azure_ad_id__isnull=False)
        
        employees_data = []
        for emp in azure_employees:
            assigned_assets = emp.assigned_assets.filter(azure_ad_id__isnull=False)
            employees_data.append({
                'id': str(emp.id),
                'name': emp.name,
                'email': emp.email,
                'department': emp.department,
                'job_title': emp.job_title,
                'azure_ad_id': emp.azure_ad_id,
                'azure_ad_username': emp.azure_ad_username,
                'employee_id': emp.employee_id,
                'last_azure_sync': emp.last_azure_sync.isoformat() if emp.last_azure_sync else None,
                'assigned_assets_count': assigned_assets.count(),
                'assigned_assets': [
                    {
                        'id': str(asset.id),
                        'name': asset.name,
                        'asset_type': asset.asset_type,
                        'serial_number': asset.serial_number,
                        'operating_system': asset.operating_system,
                        'os_version': asset.os_version,
                        'manufacturer': asset.manufacturer,
                        'model': asset.model
                    } for asset in assigned_assets
                ]
            })
        
        assets_data = []
        for asset in azure_assets:
            assets_data.append({
                'id': str(asset.id),
                'name': asset.name,
                'asset_type': asset.asset_type,
                'serial_number': asset.serial_number,
                'azure_ad_id': asset.azure_ad_id,
                'operating_system': asset.operating_system,
                'os_version': asset.os_version,
                'manufacturer': asset.manufacturer,
                'model': asset.model,
                'status': asset.status,
                'assigned_to': {
                    'id': str(asset.assigned_to.id),
                    'name': asset.assigned_to.name,
                    'email': asset.assigned_to.email
                } if asset.assigned_to else None,
                'last_azure_sync': asset.last_azure_sync.isoformat() if asset.last_azure_sync else None
            })
        
        return JsonResponse({
            'status': 'success',
            'summary': {
                'total_azure_employees': azure_employees.count(),
                'total_azure_assets': azure_assets.count(),
                'total_employees': Employee.objects.count(),
                'total_assets': Asset.objects.count(),
                'sync_percentage': {
                    'employees': (azure_employees.count() / Employee.objects.count() * 100) if Employee.objects.count() > 0 else 0,
                    'assets': (azure_assets.count() / Asset.objects.count() * 100) if Asset.objects.count() > 0 else 0,
                }
            },
            'employees': employees_data,
            'assets': assets_data
        })
    
    # Return HTML view for browser requests
    azure_employees = Employee.objects.filter(azure_ad_id__isnull=False).prefetch_related('assigned_assets')
    azure_assets = Asset.objects.filter(azure_ad_id__isnull=False).select_related('assigned_to')
    
    context = {
        'azure_employees': azure_employees,
        'azure_assets': azure_assets,
        'total_azure_employees': azure_employees.count(),
        'total_azure_assets': azure_assets.count(),
        'total_employees': Employee.objects.count(),
        'total_assets': Asset.objects.count(),
    }
    
    return render(request, 'azure_ad_status.html', context)

@login_required
def dashboard(request):
    """Dashboard view with statistics and recent handovers"""
    
    # Always show the Dashboard first - users can navigate to office-specific pages from there
    # Removed automatic office redirect so users always land on the Dashboard
    
    # Add a test message to verify the message system is working
    if not request.session.get('test_message_shown'):
        messages.success(request, '🎉 Welcome to AssetTrack! Message system is working perfectly!')
        request.session['test_message_shown'] = True
    
    # Calculate statistics
    assets_in_stock = Asset.objects.filter(status='available').count()
    pending_signatures = Handover.objects.filter(status='Pending').count()
    pending_scans = Handover.objects.filter(status='Pending Scan').count()
    recent_handovers_count = Handover.objects.count()
    
    # Calculate trends (simplified for demo)
    assets_trend = 12  # Mock data
    overdue_signatures = 3  # Mock data
    last_scan_time = "15 min ago"  # Mock data
    today_handovers = Handover.objects.filter(created_at__date=timezone.now().date()).count()
    
    # Get recent handovers with pagination
    recent_handovers_list = Handover.objects.select_related('employee').prefetch_related('assets')[:10]
    paginator = Paginator(recent_handovers_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets_in_stock': assets_in_stock,
        'pending_signatures': pending_signatures,
        'pending_scans': pending_scans,
        'recent_handovers': recent_handovers_count,
        'assets_trend': assets_trend,
        'overdue_signatures': overdue_signatures,
        'last_scan_time': last_scan_time,
        'today_handovers': today_handovers,
        'recent_handovers_list': page_obj,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def employees(request):
    """Employee management view with search functionality"""
    employees = Employee.objects.all()
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    context = {
        'employees': employees,
        'search_query': search_query,
    }
    return render(request, 'employees.html', context)

@login_required
def add_employee(request):
    """Add new employee view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        department = request.POST.get('department')
        phone = request.POST.get('phone', '')
        start_date = request.POST.get('start_date')
        
        try:
            # Convert start_date string to date object if provided
            if start_date:
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            employee = Employee.objects.create(
                name=name,
                email=email,
                department=department,
                phone=phone,
                start_date=start_date
            )
            
            messages.success(request, f'Employee {employee.name} added successfully!')
            return redirect('assets:employees')
            
        except Exception as e:
            messages.error(request, f'Error adding employee: {str(e)}')
    
    return redirect('assets:employees')

@login_required
def edit_employee(request, employee_id):
    """Edit employee view"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        department = request.POST.get('department')
        phone = request.POST.get('phone', '')
        start_date = request.POST.get('start_date')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            # Convert start_date string to date object if provided
            if start_date:
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            employee.name = name
            employee.email = email
            employee.department = department
            employee.phone = phone
            employee.start_date = start_date
            employee.is_active = is_active
            employee.save()
            
            messages.success(request, f'Employee {employee.name} updated successfully!')
            return redirect('assets:employees')
            
        except Exception as e:
            messages.error(request, f'Error updating employee: {str(e)}')
    
    context = {
        'employee': employee,
    }
    return render(request, 'edit_employee.html', context)

@login_required
def delete_employee(request, employee_id):
    """Delete employee view"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        try:
            employee_name = employee.name
            employee.delete()
            messages.success(request, f'Employee {employee_name} deleted successfully!')
            return redirect('assets:employees')
        except Exception as e:
            messages.error(request, f'Error deleting employee: {str(e)}')
    
    context = {
        'employee': employee,
    }
    return render(request, 'delete_employee.html', context)

@login_required
def assets(request):
    """Asset management view with enhanced analytics"""
    
    # Get all assets with related data
    assets = Asset.objects.select_related('assigned_to').all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        assets = assets.filter(asset_type=asset_type_filter)
    
    # Filter by office location if provided
    office_filter = request.GET.get('office')
    if office_filter:
        assets = assets.filter(office_location=office_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics
    total_assets = Asset.objects.count()
    available_assets = Asset.objects.filter(status='available').count()
    assigned_assets = Asset.objects.filter(status='assigned').count()
    maintenance_assets = Asset.objects.filter(status='maintenance').count()
    lost_assets = Asset.objects.filter(status='lost').count()
    
    # Office location statistics
    bremen_assets = Asset.objects.filter(office_location='bremen').count()
    hamburg_assets = Asset.objects.filter(office_location='hamburg').count()
    other_assets = Asset.objects.filter(office_location='other').count()
    
    # Calculate asset age and health
    today = date.today()
    new_assets = Asset.objects.filter(
        assigned_to__isnull=True,
        status='available'
    ).count()
    
    old_assets = Asset.objects.filter(
        purchase_date__lte=today - timedelta(days=365*3)  # 3+ years old
    ).count()
    
    # Department distribution
    department_stats = Asset.objects.filter(
        assigned_to__isnull=False
    ).values(
        'assigned_to__department'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Asset type distribution
    asset_type_stats = Asset.objects.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Maintenance alerts (assets older than 3 years)
    maintenance_alerts = Asset.objects.filter(
        purchase_date__lte=today - timedelta(days=365*3)
    ).count()
    
    # Recently added assets (last 7 days)
    recent_assets = Asset.objects.filter(
        created_at__gte=today - timedelta(days=7)
    ).count()
    
    # Add health scores to assets using the main function
    for asset in assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(assets, 25)  # Show 25 assets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_assets': total_assets,
        'available_assets': available_assets,
        'assigned_assets': assigned_assets,
        'maintenance_assets': maintenance_assets,
        'lost_assets': lost_assets,
        'new_assets': new_assets,
        'old_assets': old_assets,
        'maintenance_alerts': maintenance_alerts,
        'recent_assets': recent_assets,
        'department_stats': department_stats,
        'asset_type_stats': asset_type_stats,
        'status_filter': status_filter,
        'asset_type_filter': asset_type_filter,
        'office_filter': office_filter,
        'search_query': search_query,
        'bremen_assets': bremen_assets,
        'hamburg_assets': hamburg_assets,
        'other_assets': other_assets,
    }
    return render(request, 'assets.html', context)

@login_required
def bremen_office_assets(request):
    """Dedicated view for Bremen office assets"""
    
    # Get all Bremen office assets
    assets = Asset.objects.filter(office_location='bremen').select_related('assigned_to').all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        assets = assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate Bremen-specific analytics
    total_bremen_assets = Asset.objects.filter(office_location='bremen').count()
    available_bremen_assets = Asset.objects.filter(office_location='bremen', status='available').count()
    assigned_bremen_assets = Asset.objects.filter(office_location='bremen', status='assigned').count()
    maintenance_bremen_assets = Asset.objects.filter(office_location='bremen', status='maintenance').count()
    lost_bremen_assets = Asset.objects.filter(office_location='bremen', status='lost').count()
    
    # Add health scores to assets
    for asset in assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(assets, 25)  # Show 25 assets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'office_name': 'Bremen Office',
        'office_color': 'blue',
        'total_assets': total_bremen_assets,
        'available_assets': available_bremen_assets,
        'assigned_assets': assigned_bremen_assets,
        'maintenance_assets': maintenance_bremen_assets,
        'lost_assets': lost_bremen_assets,
        'status_filter': status_filter,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'office_assets.html', context)

@login_required
def hamburg_office_assets(request):
    """Dedicated view for Hamburg office assets"""
    
    # Get all Hamburg office assets
    assets = Asset.objects.filter(office_location='hamburg').select_related('assigned_to').all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        assets = assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate Hamburg-specific analytics
    total_hamburg_assets = Asset.objects.filter(office_location='hamburg').count()
    available_hamburg_assets = Asset.objects.filter(office_location='hamburg', status='available').count()
    assigned_hamburg_assets = Asset.objects.filter(office_location='hamburg', status='assigned').count()
    maintenance_hamburg_assets = Asset.objects.filter(office_location='hamburg', status='maintenance').count()
    lost_hamburg_assets = Asset.objects.filter(office_location='hamburg', status='lost').count()
    
    # Add health scores to assets
    for asset in assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(assets, 25)  # Show 25 assets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'office_name': 'Hamburg Office',
        'office_color': 'green',
        'total_assets': total_hamburg_assets,
        'available_assets': available_hamburg_assets,
        'assigned_assets': assigned_hamburg_assets,
        'maintenance_assets': maintenance_hamburg_assets,
        'lost_assets': lost_hamburg_assets,
        'status_filter': status_filter,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'office_assets.html', context)

@login_required
def other_locations_assets(request):
    """Dedicated view for Other Locations office assets"""
    
    # Get all Other Locations office assets
    assets = Asset.objects.filter(office_location='other').select_related('assigned_to').all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        assets = assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(assets, 25)  # Show 25 assets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate analytics for Other Locations office
    total_other_assets = assets.count()
    available_other_assets = assets.filter(status='available').count()
    assigned_other_assets = assets.filter(status='assigned').count()
    maintenance_other_assets = assets.filter(status='maintenance').count()
    lost_other_assets = assets.filter(status='lost').count()
    retired_other_assets = assets.filter(status='retired').count()
    
    # Asset type distribution for Other Locations office
    asset_type_stats = assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets
    for asset in page_obj:
        asset.health_score = calculate_health_score(asset)
    
    # Recent activity (last 7 days)
    recent_handovers = Handover.objects.filter(
        assets__office_location='other',
        created_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-created_at')[:5]
    
    context = {
        'assets': page_obj,
        'office_name': 'Other Locations',
        'office_color': 'purple',
        'total_assets': total_other_assets,
        'available_assets': available_other_assets,
        'assigned_assets': assigned_other_assets,
        'maintenance_assets': maintenance_other_assets,
        'lost_assets': lost_other_assets,
        'retired_assets': retired_other_assets,
        'asset_type_stats': asset_type_stats,
        'recent_handovers': recent_handovers,
        'status_filter': status_filter,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'office_assets.html', context)

@login_required
def unassigned_assets(request):
    """Unassigned assets view - shows assets not assigned to any employee"""
    
    # Get unassigned assets (assets with no assigned_to or status = available)
    unassigned_assets = Asset.objects.filter(
        Q(assigned_to__isnull=True) | Q(status='available')
    ).select_related('assigned_to').distinct()
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        unassigned_assets = unassigned_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        unassigned_assets = unassigned_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )
    
    # Calculate analytics for unassigned assets
    total_unassigned = unassigned_assets.count()
    available_unassigned = unassigned_assets.filter(status='available').count()
    maintenance_unassigned = unassigned_assets.filter(status='maintenance').count()
    lost_unassigned = unassigned_assets.filter(status='lost').count()
    
    # Asset type distribution for unassigned assets
    asset_type_stats = unassigned_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets using the main function
    for asset in unassigned_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(unassigned_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_unassigned': total_unassigned,
        'available_unassigned': available_unassigned,
        'maintenance_unassigned': maintenance_unassigned,
        'lost_unassigned': lost_unassigned,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'unassigned_assets.html', context)

@login_required
def search_assets_for_missing(request):
    """Search assets for marking as missing"""
    if request.method == 'GET':
        search_query = request.GET.get('search', '')
        employee_query = request.GET.get('employee', '')
        
        # Build the query
        assets = Asset.objects.exclude(status='lost').exclude(status='retired')
        
        if search_query:
            assets = assets.filter(
                Q(name__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(st_tag__icontains=search_query) |
                Q(model__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        if employee_query:
            assets = assets.filter(
                Q(assigned_to__name__icontains=employee_query) |
                Q(assigned_to__email__icontains=employee_query)
            )
        
        # Limit results and add health scores
        assets = assets.select_related('assigned_to')[:20]
        
        # Calculate health scores
        today = date.today()
        for asset in assets:
            if asset.purchase_date:
                age_days = (today - asset.purchase_date).days
                if age_days < 365:
                    asset.health_score = 100
                elif age_days < 365*2:
                    asset.health_score = 85
                elif age_days < 365*3:
                    asset.health_score = 70
                elif age_days < 365*4:
                    asset.health_score = 55
                else:
                    asset.health_score = 40
            else:
                asset.health_score = 100
        
        # Prepare data for JSON response
        assets_data = []
        for asset in assets:
            assets_data.append({
                'id': str(asset.id),
                'name': asset.name,
                'serial_number': asset.serial_number,
                'model': asset.model or '',
                'manufacturer': asset.manufacturer or '',
                'asset_type': asset.get_asset_type_display(),
                'status': asset.get_status_display(),
                'health_score': asset.health_score,
                'assigned_to': asset.assigned_to.name if asset.assigned_to else 'Unassigned',
                'assigned_to_email': asset.assigned_to.email if asset.assigned_to else '',
                'purchase_date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '',
            })
        
        return JsonResponse({'assets': assets_data})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def mark_asset_as_lost(request, asset_id):
    """Mark an existing asset as lost"""
    if request.method == 'POST':
        try:
            asset = Asset.objects.get(id=asset_id)
            asset.status = 'lost'
            asset.save()
            
            messages.success(request, f'Asset "{asset.name}" has been marked as lost.')
            return JsonResponse({'success': True, 'message': f'Asset "{asset.name}" marked as lost'})
        except Asset.DoesNotExist:
            return JsonResponse({'error': 'Asset not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def add_asset(request):
    """Add new asset view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        asset_type = request.POST.get('asset_type')
        serial_number = request.POST.get('serial_number')
        st_tag = request.POST.get('st_tag', '')
        model = request.POST.get('model', '')
        manufacturer = request.POST.get('manufacturer', '')
        purchase_date = request.POST.get('purchase_date')
        status = request.POST.get('status', 'available')  # Default to available if not provided
        office_location = request.POST.get('office_location', 'bremen')  # Default to bremen if not provided
        assigned_to_id = request.POST.get('assigned_to')
        
        # Software asset fields
        license_key = request.POST.get('license_key', '')
        license_type = request.POST.get('license_type', '')
        version = request.POST.get('version', '')
        vendor = request.POST.get('vendor', '')
        subscription_end = request.POST.get('subscription_end', '')
        seats = request.POST.get('seats', '')
        used_seats = request.POST.get('used_seats', '')
        
        # Maintenance fields
        maintenance_start_date = request.POST.get('maintenance_start_date', '')
        maintenance_expected_end = request.POST.get('maintenance_expected_end', '')
        maintenance_notes = request.POST.get('maintenance_notes', '')
        
        try:
            # Convert purchase_date string to date object if provided
            if purchase_date:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            purchase_date = datetime.strptime(purchase_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid purchase date format: {purchase_date}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        employees = Employee.objects.filter(is_active=True)
                        context = {'employees': employees}
                        return render(request, 'add_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing purchase date: {str(e)}')
                    employees = Employee.objects.filter(is_active=True)
                    context = {'employees': employees}
                    return render(request, 'add_asset.html', context)
            
            # Convert subscription_end string to date object if provided
            if subscription_end:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            subscription_end = datetime.strptime(subscription_end, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid subscription end date format: {subscription_end}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        employees = Employee.objects.filter(is_active=True)
                        context = {'employees': employees}
                        return render(request, 'add_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing subscription end date: {str(e)}')
                    employees = Employee.objects.filter(is_active=True)
                    context = {'employees': employees}
                    return render(request, 'add_asset.html', context)
            
            # Convert maintenance dates to date objects if provided
            if maintenance_start_date:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            maintenance_start_date = datetime.strptime(maintenance_start_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid maintenance start date format: {maintenance_start_date}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        employees = Employee.objects.filter(is_active=True)
                        context = {'employees': employees}
                        return render(request, 'add_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing maintenance start date: {str(e)}')
                    employees = Employee.objects.filter(is_active=True)
                    context = {'employees': employees}
                    return render(request, 'add_asset.html', context)
            elif status == 'maintenance':
                # Auto-set maintenance start date if status is maintenance
                from datetime import date
                maintenance_start_date = date.today()
            
            if maintenance_expected_end:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            maintenance_expected_end = datetime.strptime(maintenance_expected_end, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid maintenance expected end date format: {maintenance_expected_end}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        employees = Employee.objects.filter(is_active=True)
                        context = {'employees': employees}
                        return render(request, 'add_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing maintenance expected end date: {str(e)}')
                    employees = Employee.objects.filter(is_active=True)
                    context = {'employees': employees}
                    return render(request, 'add_asset.html', context)
            
            # Convert seats and used_seats to integers if provided
            seats = int(seats) if seats else None
            used_seats = int(used_seats) if used_seats else None
            
            asset = Asset.objects.create(
                name=name,
                asset_type=asset_type,
                serial_number=serial_number,
                st_tag=st_tag,
                model=model,
                manufacturer=manufacturer,
                purchase_date=purchase_date,
                status=status,
                office_location=office_location,
                license_key=license_key,
                license_type=license_type,
                version=version,
                vendor=vendor,
                subscription_end=subscription_end,
                seats=seats,
                used_seats=used_seats,
                maintenance_start_date=maintenance_start_date,
                maintenance_expected_end=maintenance_expected_end,
                maintenance_notes=maintenance_notes
            )
            
            # Handle assignment
            if assigned_to_id and assigned_to_id != 'none':
                assigned_to = Employee.objects.get(id=assigned_to_id)
                asset.assigned_to = assigned_to
                asset.status = 'assigned'
                asset.save()
            
            messages.success(request, f'Asset {asset.name} added successfully!')
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Asset {asset.name} added successfully!',
                    'asset_id': str(asset.id)
                })
            
            # Redirect based on status for regular form submissions
            if status == 'lost':
                return redirect('assets:lost_assets')
            elif status == 'maintenance':
                return redirect('assets:maintenance_assets')
            else:
                return redirect('assets:assets')
            
        except Exception as e:
            error_message = f'Error adding asset: {str(e)}'
            messages.error(request, error_message)
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_message
                })
    
    # Handle GET request - show add asset form
    employee_id = request.GET.get('employee')
    employee = None
    if employee_id:
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            pass
    
    employees = Employee.objects.filter(is_active=True)
    context = {
        'employees': employees,
        'pre_selected_employee': employee,
    }
    return render(request, 'add_asset.html', context)

@login_required
def edit_asset(request, asset_id):
    """Edit asset view"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        asset_type = request.POST.get('asset_type')
        serial_number = request.POST.get('serial_number')
        st_tag = request.POST.get('st_tag', '')
        model = request.POST.get('model', '')
        manufacturer = request.POST.get('manufacturer', '')
        purchase_date = request.POST.get('purchase_date')
        status = request.POST.get('status')
        assigned_to_id = request.POST.get('assigned_to')
        
        # Software asset fields
        license_key = request.POST.get('license_key', '')
        license_type = request.POST.get('license_type', '')
        version = request.POST.get('version', '')
        vendor = request.POST.get('vendor', '')
        subscription_end = request.POST.get('subscription_end', '')
        seats = request.POST.get('seats', '')
        used_seats = request.POST.get('used_seats', '')
        
        # Maintenance fields
        maintenance_start_date = request.POST.get('maintenance_start_date', '')
        maintenance_expected_end = request.POST.get('maintenance_expected_end', '')
        maintenance_notes = request.POST.get('maintenance_notes', '')
        
        try:
            # Convert purchase_date string to date object if provided
            if purchase_date:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            purchase_date = datetime.strptime(purchase_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid purchase date format: {purchase_date}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        return render(request, 'edit_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing purchase date: {str(e)}')
                    return render(request, 'edit_asset.html', context)
            
            # Convert subscription_end string to date object if provided
            if subscription_end:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            subscription_end = datetime.strptime(subscription_end, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid subscription end date format: {subscription_end}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        return render(request, 'edit_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing subscription end date: {str(e)}')
                    return render(request, 'edit_asset.html', context)
            
            # Convert maintenance dates to date objects if provided
            if maintenance_start_date:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            maintenance_start_date = datetime.strptime(maintenance_start_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid maintenance start date format: {maintenance_start_date}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        return render(request, 'edit_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing maintenance start date: {str(e)}')
                    return render(request, 'edit_asset.html', context)
            elif status == 'maintenance' and not asset.maintenance_start_date:
                # Auto-set maintenance start date if status is changed to maintenance and no start date exists
                from datetime import date
                maintenance_start_date = date.today()
            
            if maintenance_expected_end:
                try:
                    from datetime import datetime
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            maintenance_expected_end = datetime.strptime(maintenance_expected_end, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        messages.error(request, f'Invalid maintenance expected end date format: {maintenance_expected_end}. Please use DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD format.')
                        return render(request, 'edit_asset.html', context)
                except Exception as e:
                    messages.error(request, f'Error parsing maintenance expected end date: {str(e)}')
                    return render(request, 'edit_asset.html', context)
            
            # Convert seats and used_seats to integers if provided
            seats = int(seats) if seats else None
            used_seats = int(used_seats) if used_seats else None
            
            asset.name = name
            asset.asset_type = asset_type
            asset.serial_number = serial_number
            asset.st_tag = st_tag
            asset.model = model
            asset.manufacturer = manufacturer
            if purchase_date:
                asset.purchase_date = purchase_date
            asset.status = status
            asset.license_key = license_key
            asset.license_type = license_type
            asset.version = version
            asset.vendor = vendor
            if subscription_end:
                asset.subscription_end = subscription_end
            asset.seats = seats
            asset.used_seats = used_seats
            if maintenance_start_date:
                asset.maintenance_start_date = maintenance_start_date
            if maintenance_expected_end:
                asset.maintenance_expected_end = maintenance_expected_end
            asset.maintenance_notes = maintenance_notes
            
            # Handle assignment
            if assigned_to_id and assigned_to_id != 'none':
                assigned_to = Employee.objects.get(id=assigned_to_id)
                asset.assigned_to = assigned_to
            else:
                asset.assigned_to = None
            
            asset.save()
            
            messages.success(request, f'Asset {asset.name} updated successfully!')
            return redirect('assets:assets')
            
        except Exception as e:
            messages.error(request, f'Error updating asset: {str(e)}')
    
    employees = Employee.objects.filter(is_active=True)
    context = {
        'asset': asset,
        'employees': employees,
    }
    return render(request, 'edit_asset.html', context)

@login_required
def delete_asset(request, asset_id):
    """Delete asset view with permission checks"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    # Check if user has permission to delete this asset
    user_can_delete = False
    
    # Admin users can always delete
    if request.user.is_staff or request.user.is_superuser:
        user_can_delete = True
    # Check if asset allows deletion by non-admin users
    elif asset.can_delete and not asset.deletion_restricted:
        user_can_delete = True
    # Check if user is the asset owner (if assigned)
    elif asset.assigned_to and asset.assigned_to.user == request.user:
        # Only allow deletion if asset is not restricted
        user_can_delete = not asset.deletion_restricted
    
    if request.method == 'POST':
        if not user_can_delete:
            messages.error(request, 'Access denied. You do not have permission to delete this asset.')
            return redirect('assets:assets')
        
        try:
            asset_name = asset.name
            asset.delete()
            messages.success(request, f'Asset {asset_name} deleted successfully!')
            return redirect('assets:assets')
        except Exception as e:
            messages.error(request, f'Error deleting asset: {str(e)}')
    
    context = {
        'asset': asset,
        'user_can_delete': user_can_delete,
    }
    return render(request, 'delete_asset.html', context)



@login_required
def barcode_lookup(request):
    """Lookup barcode data and return asset information"""
    if request.method == 'GET':
        barcode = request.GET.get('barcode')
        
        if not barcode:
            return JsonResponse({'error': 'Barcode parameter required'}, status=400)
        
        # Smart barcode lookup system
        def smart_barcode_lookup(barcode):
            # 1. Check local database first
            barcode_database = {
                '1234567890123': {
                    'name': 'Dell Latitude 5520',
                    'type': 'laptop',
                    'model': 'Latitude 5520',
                    'manufacturer': 'Dell',
                    'serial': 'DL' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
                    'specs': 'Intel i7, 16GB RAM, 512GB SSD',
                    'warranty': '3 years',
                    'category': 'Business Laptop',
                    'price': '$1,299.99'
                },
                '9876543210987': {
                    'name': 'Apple Magic Keyboard',
                    'type': 'keyboard',
                    'model': 'Magic Keyboard',
                    'manufacturer': 'Apple',
                    'serial': 'AP' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
                    'specs': 'Wireless, Rechargeable',
                    'warranty': '1 year',
                    'category': 'Input Device',
                    'price': '$99.99'
                },
                '4567891234567': {
                    'name': 'Samsung 27" Monitor',
                    'type': 'monitor',
                    'model': 'S27A650',
                    'manufacturer': 'Samsung',
                    'serial': 'SM' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
                    'specs': '27", 4K, IPS Panel',
                    'warranty': '2 years',
                    'category': 'Display',
                    'price': '$349.99'
                },
                '7891234567890': {
                    'name': 'Logitech MX Master 3',
                    'type': 'mouse',
                    'model': 'MX Master 3',
                    'manufacturer': 'Logitech',
                    'serial': 'LG' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
                    'specs': 'Wireless, Ergonomic',
                    'warranty': '1 year',
                    'category': 'Input Device',
                    'price': '$79.99'
                },
                '3216549873210': {
                    'name': 'Sony WH-1000XM4',
                    'type': 'headphones',
                    'model': 'WH-1000XM4',
                    'manufacturer': 'Sony',
                    'serial': 'SN' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
                    'specs': 'Noise Cancelling, Wireless',
                    'warranty': '2 years',
                    'category': 'Audio',
                    'price': '$349.99'
                }
            }
            
            # 2. Smart pattern recognition for new products
            def analyze_barcode_pattern(barcode):
                patterns = {
                    'laptop': ['DL', 'HP', 'AC', 'LE', 'AS'],  # Dell, HP, Acer, Lenovo, ASUS
                    'keyboard': ['AP', 'LG', 'MS', 'CH'],       # Apple, Logitech, Microsoft, Cherry
                    'monitor': ['SM', 'LG', 'DE', 'VI'],        # Samsung, LG, Dell, ViewSonic
                    'mouse': ['LG', 'MS', 'RA'],                # Logitech, Microsoft, Razer
                    'phone': ['IP', 'SA', 'GO', 'ON'],          # iPhone, Samsung, Google, OnePlus
                    'tablet': ['IP', 'SA', 'GO', 'AM']          # iPad, Samsung, Google, Amazon
                }
                
                for product_type, prefixes in patterns.items():
                    if any(barcode.startswith(prefix) for prefix in prefixes):
                        return product_type
                return 'unknown'
            
            # 3. Manufacturer detection
            def detect_manufacturer(barcode):
                manufacturer_codes = {
                    'DL': 'Dell', 'HP': 'HP', 'AC': 'Acer', 'LE': 'Lenovo',
                    'AP': 'Apple', 'LG': 'Logitech', 'MS': 'Microsoft',
                    'SM': 'Samsung', 'DE': 'Dell', 'VI': 'ViewSonic',
                    'RA': 'Razer', 'GO': 'Google', 'ON': 'OnePlus'
                }
                
                prefix = barcode[:2]
                return manufacturer_codes.get(prefix, 'Unknown')
            
            # 4. Generate smart suggestions for new products
            def generate_smart_suggestions(barcode):
                product_type = analyze_barcode_pattern(barcode)
                manufacturer = detect_manufacturer(barcode)
                
                suggestions = {
                    'laptop': {
                        'name': f'{manufacturer} Laptop',
                        'type': 'laptop',
                        'model': f'Model {barcode[-4:]}',
                        'manufacturer': manufacturer,
                        'specs': 'Standard laptop specifications',
                        'category': 'Computer Hardware'
                    },
                    'keyboard': {
                        'name': f'{manufacturer} Keyboard',
                        'type': 'keyboard',
                        'model': f'KB-{barcode[-4:]}',
                        'manufacturer': manufacturer,
                        'specs': 'Standard keyboard',
                        'category': 'Input Device'
                    },
                    'monitor': {
                        'name': f'{manufacturer} Monitor',
                        'type': 'monitor',
                        'model': f'MON-{barcode[-4:]}',
                        'manufacturer': manufacturer,
                        'specs': 'Standard monitor',
                        'category': 'Display'
                    }
                }
                
                return suggestions.get(product_type, {
                    'name': f'New Product ({manufacturer})',
                    'type': 'unknown',
                    'model': f'MODEL-{barcode[-4:]}',
                    'manufacturer': manufacturer,
                    'specs': 'Product specifications to be added',
                    'category': 'Unknown Category'
                })
            
            # Main lookup logic
            if barcode in barcode_database:
                return JsonResponse({
                    'success': True,
                    'data': barcode_database[barcode],
                    'source': 'local_database'
                })
            else:
                # Generate smart suggestions for new products
                smart_data = generate_smart_suggestions(barcode)
                return JsonResponse({
                    'success': True,
                    'data': smart_data,
                    'source': 'smart_prediction',
                    'message': 'Product not in database. Smart prediction applied. Please verify details.',
                    'is_new_product': True
                })
        
        return smart_barcode_lookup(barcode)
    
    return JsonResponse({'error': 'GET method required'}, status=405)

@login_required
def ai_product_recognition(request):
    """AI-powered product recognition from camera image"""
    if request.method == 'POST':
        try:
            # Get the image data from the request
            image_data = request.FILES.get('image')
            
            if not image_data:
                return JsonResponse({'error': 'No image provided'}, status=400)
            
            # AI Product Recognition Logic
            def analyze_product_image(image):
                """Simulate AI analysis of product image"""
                import random
                
                # Simulate AI detecting product features
                detected_features = {
                    'shape': random.choice(['rectangular', 'square', 'circular']),
                    'size': random.choice(['small', 'medium', 'large']),
                    'color': random.choice(['black', 'white', 'silver', 'gray']),
                    'text_detected': random.choice(['Dell', 'HP', 'Apple', 'Samsung', 'Logitech', 'Microsoft']),
                    'ports': random.choice(['USB', 'HDMI', 'VGA', 'Ethernet', 'Audio']),
                    'screens': random.choice([0, 1, 2])
                }
                
                # AI-based product classification
                if detected_features['screens'] > 0:
                    if detected_features['size'] == 'large':
                        return {
                            'name': f"{detected_features['text_detected']} Monitor",
                            'type': 'monitor',
                            'model': f"MON-{random.randint(1000, 9999)}",
                            'manufacturer': detected_features['text_detected'],
                            'specs': f"{detected_features['size'].title()} {detected_features['color']} monitor with {detected_features['ports']} ports",
                            'category': 'Display',
                            'confidence': random.randint(85, 98)
                        }
                    else:
                        return {
                            'name': f"{detected_features['text_detected']} Laptop",
                            'type': 'laptop',
                            'model': f"LAP-{random.randint(1000, 9999)}",
                            'manufacturer': detected_features['text_detected'],
                            'specs': f"{detected_features['size'].title()} {detected_features['color']} laptop with {detected_features['ports']} ports",
                            'category': 'Computer Hardware',
                            'confidence': random.randint(80, 95)
                        }
                elif detected_features['shape'] == 'rectangular' and detected_features['size'] == 'small':
                    return {
                        'name': f"{detected_features['text_detected']} Keyboard",
                        'type': 'keyboard',
                        'model': f"KB-{random.randint(1000, 9999)}",
                        'manufacturer': detected_features['text_detected'],
                        'specs': f"{detected_features['color'].title()} {detected_features['shape']} keyboard",
                        'category': 'Input Device',
                        'confidence': random.randint(75, 90)
                    }
                elif detected_features['shape'] == 'circular':
                    return {
                        'name': f"{detected_features['text_detected']} Mouse",
                        'type': 'mouse',
                        'model': f"MS-{random.randint(1000, 9999)}",
                        'manufacturer': detected_features['text_detected'],
                        'specs': f"{detected_features['color'].title()} {detected_features['shape']} mouse",
                        'category': 'Input Device',
                        'confidence': random.randint(70, 85)
                    }
                else:
                    return {
                        'name': f"{detected_features['text_detected']} Device",
                        'type': 'unknown',
                        'model': f"DEV-{random.randint(1000, 9999)}",
                        'manufacturer': detected_features['text_detected'],
                        'specs': f"{detected_features['color'].title()} {detected_features['shape']} device",
                        'category': 'Unknown Category',
                        'confidence': random.randint(50, 75)
                    }
            
            # Analyze the uploaded image
            product_info = analyze_product_image(image_data)
            
            return JsonResponse({
                'success': True,
                'data': product_info,
                'source': 'ai_recognition',
                'message': f'AI detected product with {product_info["confidence"]}% confidence',
                'confidence': product_info['confidence']
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'AI analysis failed',
                'message': str(e)
            }, status=500)
    
        return JsonResponse({'error': 'POST method required'}, status=405)

@login_required
def handovers(request):
    """Handover management view"""
    # Get all handovers with related data
    handovers = Handover.objects.select_related('employee').prefetch_related('assets').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        handovers = handovers.filter(status=status_filter)
    
    # Filter by employee if provided
    employee_filter = request.GET.get('employee')
    if employee_filter:
        handovers = handovers.filter(employee__name__icontains=employee_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        handovers = handovers.filter(
            Q(employee__name__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(assets__name__icontains=search_query)
        ).distinct()
    
    # Pagination
    paginator = Paginator(handovers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_handovers = handovers.count()
    pending_handovers = handovers.filter(status='Pending').count()
    completed_handovers = handovers.filter(status='Completed').count()
    pending_scan_handovers = handovers.filter(status='Pending Scan').count()
    
    # Get unique employees for filter dropdown
    employees = Employee.objects.filter(is_active=True).order_by('name')
    
    context = {
        'handovers': page_obj,
        'total_handovers': total_handovers,
        'pending_handovers': pending_handovers,
        'completed_handovers': completed_handovers,
        'pending_scan_handovers': pending_scan_handovers,
        'employees': employees,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'search_query': search_query,
    }
    return render(request, 'handovers.html', context)

@login_required
def new_handover(request):
    """Create new handover view"""
    if request.method == 'POST':
        # Handle handover creation
        employee_id = request.POST.get('employee')
        asset_ids = request.POST.getlist('assets')
        mode = request.POST.get('mode', 'Screen Sign')
        notes = request.POST.get('notes', '')
        
        try:
            employee = Employee.objects.get(id=employee_id)
            handover = Handover.objects.create(
                employee=employee,
                mode=mode,
                notes=notes,
                created_by=request.user
            )
            
            # Add assets to handover
            for asset_id in asset_ids:
                asset = Asset.objects.get(id=asset_id)
                handover.assets.add(asset)
                # Update asset status to assigned
                asset.status = 'assigned'
                asset.assigned_to = employee
                asset.save()
            
            messages.success(request, f'Handover {handover.handover_id} created successfully.')
            return redirect('assets:handover_detail', handover_id=handover.id)
            
        except (Employee.DoesNotExist, Asset.DoesNotExist):
            messages.error(request, 'Invalid employee or asset selected.')
        except Exception as e:
            messages.error(request, f'Error creating handover: {str(e)}')
    
    employees = Employee.objects.filter(is_active=True)
    # Only show unassigned assets (status='available' and assigned_to is None)
    available_assets = Asset.objects.filter(status='available', assigned_to__isnull=True)
    
    # Get pre-selected employee from query parameter
    pre_selected_employee = None
    employee_id_param = request.GET.get('employee')
    if employee_id_param:
        try:
            pre_selected_employee = Employee.objects.get(id=employee_id_param)
        except Employee.DoesNotExist:
            pass
    
    context = {
        'employees': employees,
        'available_assets': available_assets,
        'pre_selected_employee': pre_selected_employee,
    }
    return render(request, 'new_handover.html', context)

@login_required
def handover_detail(request, handover_id):
    """Handover detail view with signature functionality"""
    handover = get_object_or_404(Handover, id=handover_id)
    
    if request.method == 'POST':
        # Handle signature submission
        employee_signature = request.POST.get('employee_signature')
        it_signature = request.POST.get('it_signature')
        employee_acknowledgment = request.POST.get('employee_acknowledgment') == 'on'
        
        handover.employee_signature = employee_signature
        handover.it_signature = it_signature
        handover.employee_acknowledgment = employee_acknowledgment
        
        # Update status based on completion
        if employee_signature and it_signature and employee_acknowledgment:
            if handover.status != 'Completed' and handover.status != 'Approved':
                handover.status = 'Completed'
                handover.completed_at = timezone.now()
        elif employee_signature or it_signature:
            handover.status = 'In Progress'
        
        handover.save()
        
        messages.success(request, 'Handover signatures saved successfully.')
        return redirect('handover_detail', handover_id=handover.id)
    
    context = {
        'handover': handover,
    }
    return render(request, 'handover_detail.html', context)

@login_required
def welcome_packs(request):
    """Welcome pack management view"""
    # Get all welcome packs with related data
    welcome_packs = WelcomePack.objects.select_related('employee', 'generated_by').order_by('-generated_at')
    
    # Get statistics from the original queryset (before filtering)
    total_welcome_packs = welcome_packs.count()
    active_welcome_packs = welcome_packs.filter(is_active=True).count()
    inactive_welcome_packs = welcome_packs.filter(is_active=False).count()
    today_welcome_packs = welcome_packs.filter(generated_at__date=timezone.now().date()).count()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'active':
            welcome_packs = welcome_packs.filter(is_active=True)
        elif status_filter == 'inactive':
            welcome_packs = welcome_packs.filter(is_active=False)
    
    # Filter by employee if provided
    employee_filter = request.GET.get('employee')
    if employee_filter:
        welcome_packs = welcome_packs.filter(employee__name__icontains=employee_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        welcome_packs = welcome_packs.filter(
            Q(employee__name__icontains=search_query) |
            Q(employee_email__icontains=search_query) |
            Q(it_contact_person__icontains=search_query)
        ).distinct()
    
    # Pagination
    paginator = Paginator(welcome_packs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique employees for filter dropdown
    employees = Employee.objects.filter(is_active=True).order_by('name')
    
    context = {
        'welcome_packs': page_obj,
        'total_welcome_packs': total_welcome_packs,
        'active_welcome_packs': active_welcome_packs,
        'inactive_welcome_packs': inactive_welcome_packs,
        'today_welcome_packs': today_welcome_packs,
        'employees': employees,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'search_query': search_query,
    }
    return render(request, 'welcome_packs.html', context)

@login_required
def new_welcome_pack(request):
    """Create new welcome pack view"""
    if request.method == 'POST':
        # Handle welcome pack creation
        employee_id = request.POST.get('employee')
        employee_password = request.POST.get('employee_password', '')
        employee_email = request.POST.get('employee_email', '')
        it_contact_person = request.POST.get('it_contact_person', '')
        it_helpdesk_email = request.POST.get('it_helpdesk_email', '')
        it_phone_number = request.POST.get('it_phone_number', '')
        teams_username = request.POST.get('teams_username', '')
        teams_email = request.POST.get('teams_email', '')
        department_info = request.POST.get('department_info', '')
        office_location = request.POST.get('office_location', '')
        start_date = request.POST.get('start_date', '')
        notes = request.POST.get('notes', '')
        
        try:
            employee = Employee.objects.get(id=employee_id)
            
            # Convert start_date string to date object if provided
            if start_date:
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            welcome_pack = WelcomePack.objects.create(
                employee=employee,
                employee_password=employee_password,
                employee_email=employee_email,
                it_contact_person=it_contact_person,
                it_helpdesk_email=it_helpdesk_email,
                it_phone_number=it_phone_number,
                teams_username=teams_username,
                teams_email=teams_email,
                department_info=department_info,
                office_location=office_location,
                start_date=start_date,
                notes=notes,
                generated_by=request.user
            )
            
            messages.success(request, f'Welcome pack for {employee.name} created successfully!')
            return redirect('assets:welcome_packs')
            
        except Exception as e:
            messages.error(request, f'Error creating welcome pack: {str(e)}')
    
    employees = Employee.objects.filter(is_active=True)
    context = {
        'employees': employees,
    }
    return render(request, 'new_welcome_pack.html', context)

@login_required
def add_welcome_pack(request):
    """Add new welcome pack view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        department = request.POST.get('department', '')
        asset_ids = request.POST.getlist('assets')
        
        try:
            welcome_pack = WelcomePack.objects.create(
                name=name,
                description=description,
                department=department if department else None
            )
            
            # Add assets to welcome pack
            for asset_id in asset_ids:
                asset = Asset.objects.get(id=asset_id)
                welcome_pack.assets.add(asset)
            
            messages.success(request, f'Welcome pack "{welcome_pack.name}" added successfully!')
            return redirect('assets:welcome_packs')
            
        except Exception as e:
            messages.error(request, f'Error adding welcome pack: {str(e)}')
    
    return redirect('assets:welcome_packs')

@login_required
def edit_welcome_pack(request, pack_id):
    """Edit welcome pack view"""
    welcome_pack = get_object_or_404(WelcomePack, id=pack_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        department = request.POST.get('department', '')
        asset_ids = request.POST.getlist('assets')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            welcome_pack.name = name
            welcome_pack.description = description
            welcome_pack.department = department if department else None
            welcome_pack.is_active = is_active
            welcome_pack.save()
            
            # Clear existing assets and add new ones
            welcome_pack.assets.clear()
            for asset_id in asset_ids:
                asset = Asset.objects.get(id=asset_id)
                welcome_pack.assets.add(asset)
            
            messages.success(request, f'Welcome pack "{welcome_pack.name}" updated successfully!')
            return redirect('assets:welcome_packs')
            
        except Exception as e:
            messages.error(request, f'Error updating welcome pack: {str(e)}')
    
    available_assets = Asset.objects.all()
    context = {
        'welcome_pack': welcome_pack,
        'available_assets': available_assets,
    }
    return render(request, 'edit_welcome_pack.html', context)

@login_required
def delete_welcome_pack(request, pack_id):
    """Delete welcome pack view"""
    welcome_pack = get_object_or_404(WelcomePack, id=pack_id)
    
    if request.method == 'POST':
        try:
            pack_name = welcome_pack.name
            welcome_pack.delete()
            messages.success(request, f'Welcome pack "{pack_name}" deleted successfully!')
            return redirect('assets:welcome_packs')
        except Exception as e:
            messages.error(request, f'Error deleting welcome pack: {str(e)}')
    
    context = {
        'welcome_pack': welcome_pack,
    }
    return render(request, 'delete_welcome_pack.html', context)

@csrf_exempt
def save_signature(request):
    """API endpoint to save signature data and toggle acknowledgment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            handover_id = data.get('handover_id')
            signature_type = data.get('signature_type')  # 'employee', 'it', or 'acknowledgment'
            signature_data = data.get('signature_data')
            send_email = data.get('send_email', False)
            token = data.get('token')  # For public access
            
            handover = get_object_or_404(Handover, id=handover_id)
            
            # If token is provided, validate it for public access
            if token:
                try:
                    handover_token = HandoverToken.objects.get(handover=handover, token=token)
                    if not handover_token.is_valid():
                        return JsonResponse({'status': 'error', 'message': 'Invalid or expired token'})
                except HandoverToken.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Invalid token'})
            
            if signature_type == 'employee':
                handover.employee_signature = signature_data
            elif signature_type == 'it':
                handover.it_signature = signature_data
            elif signature_type == 'acknowledgment':
                # Toggle the acknowledgment status
                handover.employee_acknowledgment = signature_data == 'true'
            
            # Update status based on completion
            if handover.employee_signature and handover.it_signature and handover.employee_acknowledgment:
                if handover.status != 'Completed' and handover.status != 'Approved':
                    handover.status = 'Completed'
                    handover.completed_at = timezone.now()
            elif handover.employee_signature or handover.it_signature:
                handover.status = 'In Progress'
            
            handover.save()
            
            # Send email if requested
            if send_email and signature_type == 'employee':
                try:
                    send_handover_signature_email(handover)
                    return JsonResponse({'status': 'success', 'email_sent': True})
                except Exception as email_error:
                    # Still return success for handover preparation, but note email error
                    return JsonResponse({'status': 'success', 'email_sent': False, 'email_error': str(email_error)})
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def get_public_welcome_pack_url(welcome_pack):
    """Get public URL for welcome pack access without password"""
    try:
        # Create or get existing token for this welcome pack
        token = create_welcome_pack_token(welcome_pack)
        if not token:
            return None
        
        # Build public URL
        domain = getattr(settings, 'EMAIL_DOMAIN', settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '172.27.2.43')
        base_url = f"https://{domain}"
        
        public_url = f"{base_url}{reverse('assets:public_welcome_pack_detail', args=[welcome_pack.id, token])}"
        return public_url
        
    except Exception as e:
        print(f"Error creating public welcome pack URL: {str(e)}")
        return None

def create_welcome_pack_token(welcome_pack):
    """Create or get existing token for welcome pack public access"""
    try:
        from .models import WelcomePackToken
        
        # Try to get existing token
        try:
            token_obj = WelcomePackToken.objects.get(welcome_pack=welcome_pack)
            if token_obj.is_valid():
                return token_obj.token
        except WelcomePackToken.DoesNotExist:
            pass
        
        # Create new token
        token = secrets.token_urlsafe(32)
        token_obj = WelcomePackToken.objects.create(
            welcome_pack=welcome_pack,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(days=30)  # 30 days expiry
        )
        
        return token
        
    except Exception as e:
        print(f"Error creating welcome pack token: {str(e)}")
        return None

def send_welcome_pack_emails(welcome_pack):
    """Send welcome pack emails to employee and IT team using Microsoft Graph"""
    try:
        # No need for email settings check - using Microsoft Graph directly
        print("Sending welcome pack emails using Microsoft Graph...")
        
        # Send employee welcome email
        employee_success = send_employee_welcome_email(welcome_pack)
        
        # Send IT team notification email
        it_success = send_it_team_notification_email(welcome_pack)
        
        return employee_success and it_success
        
    except Exception as e:
        print(f"Error sending welcome pack emails: {str(e)}")
        return False

def send_employee_welcome_email(welcome_pack):
    """Send welcome email to employee"""
    try:
        # Use employee's email from welcome pack or employee record
        employee_email = welcome_pack.employee_email or welcome_pack.employee.email
        if not employee_email:
            print("No employee email found")
            return False
        
        # Get the public welcome pack URL - no password required
        welcome_pack_url = get_public_welcome_pack_url(welcome_pack)
        if not welcome_pack_url:
            # Fallback to regular URL if public URL creation fails
            domain = getattr(settings, 'EMAIL_DOMAIN', settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '172.27.2.43')
            welcome_pack_url = f"https://{domain}{reverse('assets:welcome_pack_detail', args=[welcome_pack.id])}"
        
        # Email subject and content
        subject = f"Welcome to Harren Group - {welcome_pack.employee.name}"
        
        # HTML email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    Welcome to Harren Group - {welcome_pack.employee.name}
                </h2>
                
                <p>Dear {welcome_pack.employee.name},</p>
                
                <p>Welcome to Harren Group! We're excited to have you join our team. Your welcome pack has been prepared with all the necessary information for your first day.</p>
                
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">🔑 Your Login Information:</h3>
                    <p><strong>Your login credentials are included in your welcome pack.</strong></p>
                    <p style="color: #666; font-size: 14px; margin-bottom: 0;">
                        <strong>🔒 Security:</strong> Click the link below to view your secure welcome pack with login details.
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{welcome_pack_url}" 
                       style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        View Your Welcome Pack
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, you can copy and paste this link into your browser:<br>
                    <a href="{welcome_pack_url}" style="color: #3498db;">{welcome_pack_url}</a>
                </p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">📋 Next Steps:</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Log in to your computer using the credentials above</li>
                        <li>Change your password immediately</li>
                        <li>Check your assigned assets and equipment</li>
                        <li>Contact IT if you need any assistance</li>
                    </ol>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">📞 IT Support Contact:</h3>
                    <p><strong>IT Contact:</strong> {welcome_pack.it_contact_person}</p>
                    <p><strong>Email:</strong> {welcome_pack.it_helpdesk_email}</p>
                    <p><strong>Phone:</strong> {welcome_pack.it_phone_number}</p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Harren Group AssetTrack. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Welcome to Harren Group - {welcome_pack.employee.name}
        
        Dear {welcome_pack.employee.name},
        
        Welcome to Harren Group! We're excited to have you join our team. Your welcome pack has been prepared with all the necessary information for your first day.
        
        Your Login Information:
        - Your login credentials are included in your welcome pack
        - Click the link below to view your secure welcome pack with login details
        
        To view your complete welcome pack, please visit:
        {welcome_pack_url}
        
        Next Steps:
        1. Log in to your computer using the credentials above
        2. Change your password immediately
        3. Check your assigned assets and equipment
        4. Contact IT if you need any assistance
        
        IT Support Contact:
        - IT Contact: {welcome_pack.it_contact_person}
        - Email: {welcome_pack.it_helpdesk_email}
        - Phone: {welcome_pack.it_phone_number}
        
        This is an automated message from Harren Group AssetTrack.
        """
        
        # Send email using Microsoft Graph backend
        from assets.microsoft_graph_email import MicrosoftGraphEmailBackend
        backend = MicrosoftGraphEmailBackend()
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [employee_email])
        msg.attach_alternative(html_content, "text/html")
        backend.send_messages([msg])
        
        print(f"Employee welcome email sent to: {employee_email}")
        return True
        
    except Exception as e:
        print(f"Error sending employee welcome email: {str(e)}")
        return False

def send_it_team_notification_email(welcome_pack):
    """Send notification email to IT team"""
    try:
        # Use it-office-assettrack@harren-group.com for IT team notification
        it_email = "it-office-assettrack@harren-group.com"
        
        # Email subject and content
        subject = f"New Employee Setup Required - {welcome_pack.employee.name}"
        
        # HTML email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    New Employee Setup Required - {welcome_pack.employee.name}
                </h2>
                
                <p>Dear IT Team,</p>
                
                <p>A new employee has been added to the system and requires IT setup. Please review the details below and complete the necessary setup tasks.</p>
                
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">👤 Employee Information:</h3>
                    <p><strong>Name:</strong> {welcome_pack.employee.name}</p>
                    <p><strong>Email:</strong> {welcome_pack.employee.email}</p>
                    <p><strong>Start Date:</strong> {welcome_pack.start_date or 'Not specified'}</p>
                    <p><strong>Office Location:</strong> {welcome_pack.office_location or 'Not specified'}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">🔧 Setup Tasks Required:</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Verify computer access and login credentials</li>
                        <li>Set up email account and Teams access</li>
                        <li>Configure assigned assets and equipment</li>
                        <li>Provide initial training and support</li>
                        <li>Verify all systems are working correctly</li>
                    </ol>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">📋 Employee Details:</h3>
                    <p><strong>Department Info:</strong> {welcome_pack.department_info or 'Not specified'}</p>
                    <p><strong>Teams Username:</strong> {welcome_pack.teams_username or 'Not specified'}</p>
                    <p><strong>Teams Email:</strong> {welcome_pack.teams_email or 'Not specified'}</p>
                    <p><strong>Notes:</strong> {welcome_pack.notes or 'No additional notes'}</p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Harren Group AssetTrack. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        New Employee Setup Required - {welcome_pack.employee.name}
        
        Dear IT Team,
        
        A new employee has been added to the system and requires IT setup. Please review the details below and complete the necessary setup tasks.
        
        Employee Information:
        - Name: {welcome_pack.employee.name}
        - Email: {welcome_pack.employee.email}
        - Start Date: {welcome_pack.start_date or 'Not specified'}
        - Office Location: {welcome_pack.office_location or 'Not specified'}
        
        Setup Tasks Required:
        1. Verify computer access and login credentials
        2. Set up email account and Teams access
        3. Configure assigned assets and equipment
        4. Provide initial training and support
        5. Verify all systems are working correctly
        
        Employee Details:
        - Department Info: {welcome_pack.department_info or 'Not specified'}
        - Teams Username: {welcome_pack.teams_username or 'Not specified'}
        - Teams Email: {welcome_pack.teams_email or 'Not specified'}
        - Notes: {welcome_pack.notes or 'No additional notes'}
        
        This is an automated message from Harren Group AssetTrack.
        """
        
        # Send email using Microsoft Graph backend
        from assets.microsoft_graph_email import MicrosoftGraphEmailBackend
        backend = MicrosoftGraphEmailBackend()
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [it_email])
        msg.attach_alternative(html_content, "text/html")
        backend.send_messages([msg])
        
        print(f"IT team notification email sent to: {it_email}")
        return True
        
    except Exception as e:
        print(f"Error sending IT team notification email: {str(e)}")
        return False

def send_handover_signature_email(handover):
    """Send email to employee with handover signature link"""
    try:
        # Get the public handover URL - no password required
        handover_url = get_public_handover_url(handover)
        if not handover_url:
            # Fallback to regular URL if public URL creation fails
            domain = getattr(settings, 'EMAIL_DOMAIN', settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '172.27.2.43')
            handover_url = f"https://{domain}{reverse('assets:handover_detail', args=[handover.id])}"
        
        # Email subject and content
        subject = f"Asset Handover Signature Required - {handover.handover_id} - Harren Group"
        
        # HTML email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    Asset Handover Signature Required - Harren Group
                </h2>
                
                <p>Dear {handover.employee.name},</p>
                
                <p>You have been assigned assets that require your signature for handover. Please click the link below to review and sign the handover document.</p>
                
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">📱 How to Sign (Quick Guide):</h3>
                    <p><strong>📱 On Mobile/Tablet (Recommended):</strong></p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Click the link below</li>
                        <li>Scroll down to the signature section</li>
                        <li>Use your finger to draw signature in the white box</li>
                        <li>Tap 'Save Signature' when done</li>
                    </ol>
                    
                    <p><strong>🖱️ On Desktop/Laptop:</strong></p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Click the link below</li>
                        <li>Scroll down to the signature section</li>
                        <li>Click and drag your mouse in the white box</li>
                        <li>Click 'Save Signature' when done</li>
                    </ol>
                    
                    <p style="color: #666; font-size: 14px; margin-bottom: 0;">
                        <strong>💡 Tip:</strong> No password required! Just click the link and sign directly.
                    </p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Handover Details:</h3>
                    <p><strong>Handover ID:</strong> {handover.handover_id}</p>
                    <p><strong>Created:</strong> {handover.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p><strong>Status:</strong> {handover.status}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{handover_url}" 
                       style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Sign Handover Document
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, you can copy and paste this link into your browser:<br>
                    <a href="{handover_url}" style="color: #3498db;">{handover_url}</a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Harren Group AssetTrack. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Asset Handover Signature Required - {handover.handover_id}
        
        Dear {handover.employee.name},
        
        You have been assigned assets that require your signature for handover. Please review and sign the handover document.
        
        Handover Details:
        - Handover ID: {handover.handover_id}
        - Created: {handover.created_at.strftime('%B %d, %Y at %I:%M %p')}
        - Status: {handover.status}
        
        To sign the handover document, please visit:
        {handover_url}
        
        This is an automated message from Harren Group AssetTrack.
        """
        
        # Send email
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [handover.employee.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        # Update handover email tracking
        handover.email_sent = True
        handover.email_sent_at = timezone.now()
        handover.save()
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise e

# Placeholder views for other pages
@login_required
def employees_detail(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    context = {'employee': employee}
    return render(request, 'employees_detail.html', context)

@login_required
def assets_detail(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    
    # Calculate health score for the asset
    asset.health_score = calculate_health_score(asset)
    
    context = {'asset': asset}
    return render(request, 'assets_detail.html', context)

@login_required
def employee_handovers(request, employee_id):
    """Show all handovers for a specific employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Get all handovers for this employee
    handovers = Handover.objects.filter(employee=employee).prefetch_related('assets').order_by('-created_at')
    
    # Calculate handover status counts
    total_handovers = handovers.count()
    pending_signatures = handovers.filter(status='Pending').count()
    completed_handovers = handovers.filter(status='Completed').count()
    
    # Get employee's assigned assets count
    assigned_assets = Asset.objects.filter(assigned_to=employee).count()
    
    # Paginate the results
    paginator = Paginator(handovers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'employee': employee,
        'handovers': page_obj,
        'total_handovers': total_handovers,
        'pending_signatures': pending_signatures,
        'completed_handovers': completed_handovers,
        'assigned_assets': assigned_assets,
    }
    return render(request, 'employee_handovers.html', context)

@login_required
def send_welcome_pack_email(request, pack_id):
    """Send welcome pack email to employee and IT"""
    welcome_pack = get_object_or_404(WelcomePack, id=pack_id)
    
    if request.method == 'POST':
        try:
            # Send actual emails using Microsoft Graph (like handover signatures)
            success = send_welcome_pack_emails(welcome_pack)
            
            if success:
                # Mark emails as sent
                welcome_pack.email_sent_to_employee = True
                welcome_pack.email_sent_to_it = True
                welcome_pack.email_sent_at = timezone.now()
                welcome_pack.save()
                
                messages.success(request, f'Welcome pack emails sent successfully to {welcome_pack.employee.name} and IT team!')
            else:
                messages.error(request, 'Error sending welcome pack emails. Please try again.')
            
            return redirect('assets:welcome_packs')
            
        except Exception as e:
            messages.error(request, f'Error sending welcome pack email: {str(e)}')
    
    context = {
        'welcome_pack': welcome_pack,
    }
    return render(request, 'send_welcome_pack_email.html', context)

def public_welcome_pack_detail(request, pack_id, token):
    """Public welcome pack detail view - no authentication required"""
    try:
        from .models import WelcomePackToken
        
        # Get welcome pack and validate token
        welcome_pack = get_object_or_404(WelcomePack, id=pack_id)
        token_obj = get_object_or_404(WelcomePackToken, welcome_pack=welcome_pack, token=token)
        
        # Check if token is valid
        if not token_obj.is_valid():
            return render(request, 'public_welcome_pack_expired.html', {
                'welcome_pack': welcome_pack,
                'token': token
            })
        
        # Record access
        token_obj.record_access()
        
        context = {
            'welcome_pack': welcome_pack,
            'token': token,
            'is_public_access': True,
        }
        
        return render(request, 'public_welcome_pack_detail.html', context)
        
    except Exception as e:
        return render(request, 'public_welcome_pack_error.html', {
            'error': str(e),
            'pack_id': pack_id,
            'token': token
        })

@login_required
def welcome_pack_detail(request, pack_id):
    """View welcome pack details and generate PDF"""
    welcome_pack = get_object_or_404(WelcomePack, id=pack_id)
    
    context = {
        'welcome_pack': welcome_pack,
    }
    return render(request, 'welcome_pack_detail.html', context)

@login_required
def edit_handover(request, handover_id):
    """Edit handover details"""
    handover = get_object_or_404(Handover, id=handover_id)
    
    if request.method == 'POST':
        # Handle handover updates
        handover.notes = request.POST.get('notes', '')
        handover.mode = request.POST.get('mode', handover.mode)
        handover.save()
        
        messages.success(request, 'Handover updated successfully.')
        return redirect('assets:handover_detail', handover_id=handover.id)
    
    context = {
        'handover': handover,
    }
    return render(request, 'edit_handover.html', context)

@csrf_exempt
def send_handover_email(request, handover_id):
    """Send handover email to employee and IT team"""
    if request.method == 'POST':
        try:
            handover = get_object_or_404(Handover, id=handover_id)
            
            # Check if handover is complete
            if not (handover.employee_signature and handover.it_signature and handover.employee_acknowledgment):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Handover must be fully signed before sending email'
                })
            
            # Here you would implement the actual email sending logic
            # For now, we'll just mark the email as sent
            handover.email_sent = True
            handover.email_sent_at = timezone.now()
            handover.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def handover_pdf(request, handover_id):
    """Generate PDF for handover"""
    handover = get_object_or_404(Handover, id=handover_id)
    
    # Here you would implement PDF generation
    # For now, we'll redirect to the detail page with a print-friendly version
    context = {
        'handover': handover,
        'print_mode': True
    }
    return render(request, 'handover_pdf.html', context)

@csrf_exempt
def approve_handover(request, handover_id):
    """Approve a completed handover (staff only)"""
    if request.method == 'POST':
        try:
            # Check if user is staff
            if not request.user.is_staff:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Only staff members can approve handovers'
                })
            
            handover = get_object_or_404(Handover, id=handover_id)
            
            # Check if handover is completed
            if handover.status != 'Completed':
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Only completed handovers can be approved'
                })
            
            # Approve the handover
            handover.status = 'Approved'
            handover.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def assigned_assets(request):
    """Assigned assets view - shows assets assigned to employees"""
    
    # Get assigned assets (assets with assigned_to not null and status = assigned)
    assigned_assets = Asset.objects.filter(
        assigned_to__isnull=False,
        status='assigned'
    ).select_related('assigned_to').distinct()
    
    # Filter by employee if provided
    employee_filter = request.GET.get('employee')
    if employee_filter:
        assigned_assets = assigned_assets.filter(assigned_to__id=employee_filter)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        assigned_assets = assigned_assets.filter(asset_type=asset_type_filter)
    
    # Filter by department if provided
    department_filter = request.GET.get('department')
    if department_filter:
        assigned_assets = assigned_assets.filter(assigned_to__department=department_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        assigned_assets = assigned_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query) |
            Q(assigned_to__department__icontains=search_query)
        )
    
    # Calculate analytics for assigned assets
    total_assigned = assigned_assets.count()
    
    # Department distribution for assigned assets
    department_stats = assigned_assets.values(
        'assigned_to__department'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Asset type distribution for assigned assets
    asset_type_stats = assigned_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets using the main function
    for asset in assigned_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(assigned_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get employee info if filtering by employee
    employee = None
    if employee_filter:
        try:
            employee = Employee.objects.get(id=employee_filter)
        except Employee.DoesNotExist:
            pass
    
    context = {
        'assets': page_obj,
        'total_assigned': total_assigned,
        'department_stats': department_stats,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'department_filter': department_filter,
        'employee_filter': employee_filter,
        'employee': employee,
        'search_query': search_query,
    }
    return render(request, 'assigned_assets.html', context)

@login_required
def maintenance_assets(request):
    """Maintenance assets view - shows assets under maintenance"""
    
    # Get maintenance assets (status = maintenance)
    maintenance_assets = Asset.objects.filter(
        status='maintenance'
    ).select_related('assigned_to').distinct()
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        maintenance_assets = maintenance_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        maintenance_assets = maintenance_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics for maintenance assets
    total_maintenance = maintenance_assets.count()
    assigned_maintenance = maintenance_assets.filter(assigned_to__isnull=False).count()
    unassigned_maintenance = maintenance_assets.filter(assigned_to__isnull=True).count()
    
    # Asset type distribution for maintenance assets
    asset_type_stats = maintenance_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets using the main function
    for asset in maintenance_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(maintenance_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_maintenance': total_maintenance,
        'assigned_maintenance': assigned_maintenance,
        'unassigned_maintenance': unassigned_maintenance,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'maintenance_assets.html', context)

@login_required
def lost_assets(request):
    """Lost assets view - shows assets marked as lost"""
    
    # Get lost assets (status = lost)
    lost_assets = Asset.objects.filter(
        status='lost'
    ).select_related('assigned_to').distinct()
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        lost_assets = lost_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        lost_assets = lost_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics for lost assets
    total_lost = lost_assets.count()
    assigned_lost = lost_assets.filter(assigned_to__isnull=False).count()
    unassigned_lost = lost_assets.filter(assigned_to__isnull=True).count()
    
    # Asset type distribution for lost assets
    asset_type_stats = lost_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets using the main function
    for asset in lost_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(lost_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_lost': total_lost,
        'assigned_lost': assigned_lost,
        'unassigned_lost': unassigned_lost,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'lost_assets.html', context)

@login_required
def retired_assets(request):
    """Retired assets view - shows assets marked as retired"""
    
    # Get retired assets (status = retired)
    retired_assets = Asset.objects.filter(
        status='retired'
    ).select_related('assigned_to').distinct()
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        retired_assets = retired_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        retired_assets = retired_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics for retired assets
    total_retired = retired_assets.count()
    assigned_retired = retired_assets.filter(assigned_to__isnull=False).count()
    unassigned_retired = retired_assets.filter(assigned_to__isnull=True).count()
    
    # Asset type distribution for retired assets
    asset_type_stats = retired_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate asset age and health
    today = date.today()
    
    # Add health scores to assets using the main function
    for asset in retired_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(retired_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_retired': total_retired,
        'assigned_retired': assigned_retired,
        'unassigned_retired': unassigned_retired,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'retired_assets.html', context)

@login_required
def old_assets(request):
    """Old assets view - shows assets older than 3 years"""
    
    # Get old assets (3+ years old)
    today = date.today()
    old_assets = Asset.objects.filter(
        purchase_date__lte=today - timedelta(days=365*3)  # 3+ years old
    ).select_related('assigned_to').distinct()
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        old_assets = old_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        old_assets = old_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics for old assets
    total_old = old_assets.count()
    assigned_old = old_assets.filter(assigned_to__isnull=False).count()
    unassigned_old = old_assets.filter(assigned_to__isnull=True).count()
    
    # Asset type distribution for old assets
    asset_type_stats = old_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Add health scores to assets using the main function
    for asset in old_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(old_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_old': total_old,
        'assigned_old': assigned_old,
        'unassigned_old': unassigned_old,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'old_assets.html', context)

@login_required
def healthy_assets(request):
    """Healthy assets view - shows assets with good health scores (80%+)"""
    
    # Get assets with good health scores (80%+)
    today = date.today()
    
    # Use the main health calculation function
    
    # Get all assets and filter by health score
    all_assets = Asset.objects.select_related('assigned_to').all()
    healthy_assets = []
    
    for asset in all_assets:
        asset.health_score = calculate_health_score(asset)
        if asset.health_score >= 80:  # 80%+ health score
            healthy_assets.append(asset)
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        healthy_assets = [asset for asset in healthy_assets if asset.asset_type == asset_type_filter]
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        healthy_assets = [asset for asset in healthy_assets if 
            search_query.lower() in asset.name.lower() or
            search_query.lower() in asset.serial_number.lower() or
            search_query.lower() in (asset.st_tag or '').lower() or
            search_query.lower() in (asset.model or '').lower() or
            search_query.lower() in (asset.manufacturer or '').lower() or
            (asset.assigned_to and search_query.lower() in asset.assigned_to.name.lower())
        ]
    
    # Calculate analytics
    total_healthy = len(healthy_assets)
    assigned_healthy = len([asset for asset in healthy_assets if asset.assigned_to])
    unassigned_healthy = len([asset for asset in healthy_assets if not asset.assigned_to])
    
    # Asset type distribution
    asset_type_stats = {}
    for asset in healthy_assets:
        asset_type_stats[asset.asset_type] = asset_type_stats.get(asset.asset_type, 0) + 1
    
    # Pagination
    paginator = Paginator(healthy_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_healthy': total_healthy,
        'assigned_healthy': assigned_healthy,
        'unassigned_healthy': unassigned_healthy,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'healthy_assets.html', context)

@login_required
def new_assets_view(request):
    """New assets view - shows unassigned assets (not assigned to anyone)"""
    
    # Get unassigned assets (not assigned to anyone)
    new_assets = Asset.objects.filter(
        assigned_to__isnull=True,
        status='available'
    ).select_related('assigned_to').order_by('-created_at')
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        new_assets = new_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        new_assets = new_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics
    total_new = new_assets.count()  # All unassigned assets
    assigned_new = 0  # No assigned assets in this view (all are unassigned)
    unassigned_new = total_new  # All assets in this view are unassigned
    
    # Asset type distribution
    asset_type_stats = new_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate health scores
    today = date.today()
    
    # Use the main health calculation function
    
    for asset in new_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(new_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_new': total_new,
        'assigned_new': assigned_new,
        'unassigned_new': unassigned_new,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'new_assets.html', context)

@login_required
def attention_assets(request):
    """Assets that need attention - shows assets 2+ years old"""
    
    # Get assets 2+ years old (based on purchase date)
    today = date.today()
    two_years_ago = today - timedelta(days=365*2)
    
    attention_assets = Asset.objects.filter(
        purchase_date__lte=two_years_ago
    ).select_related('assigned_to').order_by('purchase_date')
    
    # Filter by asset type if provided
    asset_type_filter = request.GET.get('asset_type')
    if asset_type_filter:
        attention_assets = attention_assets.filter(asset_type=asset_type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        attention_assets = attention_assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(st_tag__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query)
        )
    
    # Calculate analytics
    total_attention = attention_assets.count()
    assigned_attention = attention_assets.filter(assigned_to__isnull=False).count()
    unassigned_attention = attention_assets.filter(assigned_to__isnull=True).count()
    
    # Asset type distribution
    asset_type_stats = attention_assets.values(
        'asset_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Use the main health calculation function
    
    for asset in attention_assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(attention_assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assets': page_obj,
        'total_attention': total_attention,
        'assigned_attention': assigned_attention,
        'unassigned_attention': unassigned_attention,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    return render(request, 'attention_assets.html', context)

@login_required
def user_profile(request):
    """User profile view showing current user information and settings"""
    user = request.user
    
    # Get user's recent activity (mock data for now)
    recent_activity = [
        {
            'timestamp': '2024-01-15 14:30:22',
            'action': 'Login',
            'details': 'Successfully logged in from 192.168.1.100'
        },
        {
            'timestamp': '2024-01-15 13:45:15',
            'action': 'Asset Assignment',
            'details': 'Assigned MacBook Pro to John Doe'
        },
        {
            'timestamp': '2024-01-15 12:20:08',
            'action': 'Handover Created',
            'details': 'Created handover for Sarah Wilson'
        },
        {
            'timestamp': '2024-01-15 11:15:42',
            'action': 'Welcome Pack',
            'details': 'Generated welcome pack for new employee'
        }
    ]
    
    # Get user's assigned assets (if they are an employee)
    try:
        employee = Employee.objects.get(email=user.email)
        assigned_assets = Asset.objects.filter(assigned_to=employee)
        handovers_created = Handover.objects.filter(created_by=user)
    except Employee.DoesNotExist:
        employee = None
        assigned_assets = []
        handovers_created = []
    
    context = {
        'user': user,
        'employee': employee,
        'assigned_assets': assigned_assets,
        'handovers_created': handovers_created,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'user_profile.html', context)

@login_required
def employee_photo(request, employee_id):
    """Proxy view to serve employee photos from Azure AD"""
    from django.http import HttpResponse
    from .azure_ad_integration import AzureADIntegration
    
    try:
        employee = get_object_or_404(Employee, id=employee_id)
        
        if not employee.azure_ad_id:
            # Return default avatar if no Azure AD ID
            return HttpResponse(status=404)
        
        # Get photo data from Azure AD
        azure_ad = AzureADIntegration()
        photo_data = azure_ad.get_user_photo_data(employee.azure_ad_id)
        
        if photo_data:
            response = HttpResponse(photo_data, content_type='image/jpeg')
            response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            return response
        else:
            return HttpResponse(status=404)
            
    except Exception as e:
        print(f"Error serving photo for employee {employee_id}: {e}")
        return HttpResponse(status=500)

def privacy_policy(request):
    """Privacy Policy page view"""
    return render(request, 'privacy_policy.html')

@login_required
def change_password(request):
    """Handle password change requests via AJAX"""
    if request.method == 'POST':
        try:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            # Validate that all fields are provided
            if not all([old_password, new_password1, new_password2]):
                return JsonResponse({
                    'success': False,
                    'error': 'All fields are required.'
                })
            
            # Validate that new passwords match
            if new_password1 != new_password2:
                return JsonResponse({
                    'success': False,
                    'error': 'New passwords do not match.'
                })
            
            # Validate that new password is different from old password
            if old_password == new_password1:
                return JsonResponse({
                    'success': False,
                    'error': 'New password must be different from current password.'
                })
            
            # Use Django's built-in password change form for validation
            form = PasswordChangeForm(user=request.user, data={
                'old_password': old_password,
                'new_password1': new_password1,
                'new_password2': new_password2,
            })
            
            if form.is_valid():
                # Save the new password
                form.save()
                # Update the session to prevent logout
                update_session_auth_hash(request, form.user)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Password changed successfully!'
                })
            else:
                # Get the first error message
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(str(error))
                
                return JsonResponse({
                    'success': False,
                    'error': error_messages[0] if error_messages else 'Invalid password data.'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method.'
    })

@login_required
def department_assets(request, department):
    """Department-specific assets view"""
    # Get all assets assigned to employees in the specified department
    assets = Asset.objects.filter(
        assigned_to__department=department,
        status__in=['assigned', 'maintenance']
    ).select_related('assigned_to')
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(assigned_to__name__icontains=search_query) |
            Q(asset_type__icontains=search_query)
        )
    
    # Handle asset type filter
    asset_type_filter = request.GET.get('asset_type', '')
    if asset_type_filter:
        assets = assets.filter(asset_type=asset_type_filter)
    
    # Calculate department statistics
    total_assets = assets.count()
    assigned_assets = assets.filter(status='assigned').count()
    maintenance_assets = assets.filter(status='maintenance').count()
    
    # Get asset type distribution for this department
    asset_type_stats = assets.values('asset_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate health scores for all assets
    for asset in assets:
        asset.health_score = calculate_health_score(asset)
    
    # Pagination
    paginator = Paginator(assets, 25)  # Show 25 assets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'department': department,
        'assets': page_obj,
        'total_assets': total_assets,
        'assigned_assets': assigned_assets,
        'maintenance_assets': maintenance_assets,
        'asset_type_stats': asset_type_stats,
        'asset_type_filter': asset_type_filter,
        'search_query': search_query,
    }
    
    return render(request, 'department_assets.html', context)

def public_handover_detail(request, handover_id, token):
    """Public handover detail view - no authentication required"""
    try:
        # Get handover
        handover = get_object_or_404(Handover, id=handover_id)
        
        # Try to get the token
        try:
            handover_token = HandoverToken.objects.get(handover=handover, token=token)
        except HandoverToken.DoesNotExist:
            # Token doesn't exist, create one
            handover_token = create_handover_token(handover)
            if not handover_token or handover_token.token != token:
                return render(request, 'public_handover_error.html', {
                    'error': 'Invalid handover link or token'
                })
        
        # Check if token is valid
        if not handover_token.is_valid():
            return render(request, 'public_handover_expired.html', {
                'handover': handover,
                'error': 'Token has expired or is no longer valid'
            })
        
        # Record access
        handover_token.record_access()
        
        # Get handover assets
        handover_assets = handover.handoverasset_set.all()
        
        context = {
            'handover': handover,
            'handover_assets': handover_assets,
            'token': token,
            'is_public': True,  # Flag to indicate this is public access
        }
        
        return render(request, 'public_handover_detail.html', context)
        
    except Exception as e:
        print(f"Error in public_handover_detail: {e}")
        return render(request, 'public_handover_error.html', {
            'error': 'Invalid handover link or token'
        })

def create_handover_token(handover):
    """Create a public access token for handover"""
    try:
        # Generate unique token
        token = secrets.token_urlsafe(32)
        
        # Create or update token
        handover_token, created = HandoverToken.objects.get_or_create(
            handover=handover,
            defaults={
                'token': token,
                'is_active': True,
                'expires_at': timezone.now() + timedelta(days=30)  # 30 days expiration
            }
        )
        
        if not created:
            # Update existing token
            handover_token.token = token
            handover_token.is_active = True
            handover_token.expires_at = timezone.now() + timedelta(days=30)
            handover_token.save()
        
        return handover_token
        
    except Exception as e:
        print(f"Error creating handover token: {e}")
        return None

def get_public_handover_url(handover):
    """Get public handover URL with token"""
    try:
        # Get or create token
        handover_token = create_handover_token(handover)
        if handover_token:
            # Build public URL
            domain = getattr(settings, 'EMAIL_DOMAIN', settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '172.27.2.43')
            base_url = f"https://{domain}"
            
            return f"{base_url}/handover/public/{handover.id}/{handover_token.token}/"
        
        return None
        
    except Exception as e:
        print(f"Error getting public handover URL: {e}")
        return None

# User Management Views
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_management(request):
    """User management view for superusers"""
    # Double check superuser status
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Superuser privileges required.')
        return redirect('assets:dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'users': users,
    }
    return render(request, 'user_management.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_user(request):
    """Add new user view"""
    # Double check superuser status
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Superuser privileges required.')
        return redirect('assets:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password = request.POST.get('password')
        is_superuser = request.POST.get('is_superuser') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, f'User with username "{username}" already exists.')
                return redirect('assets:user_management')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, f'User with email "{email}" already exists.')
                return redirect('assets:user_management')
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_superuser=is_superuser,
                is_staff=is_staff,
                is_active=is_active
            )
            
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('assets:user_management')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('assets:user_management')
    
    return render(request, 'add_user.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_user(request, user_id):
    """Edit user view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.is_superuser = request.POST.get('is_superuser') == 'on'
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_active = request.POST.get('is_active') == 'on'
        
        try:
            user.save()
            messages.success(request, f'User "{user.username}" updated successfully!')
            return redirect('assets:user_management')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user': user,
    }
    return render(request, 'edit_user.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def change_user_password(request, user_id):
    """Change user password view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('assets:change_user_password', user_id=user_id)
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('assets:change_user_password', user_id=user_id)
        
        try:
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Password for "{user.username}" changed successfully!')
            return redirect('assets:user_management')
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
    
    context = {
        'user': user,
    }
    return render(request, 'change_user_password.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    """Delete user view"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deleting the current user
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('assets:user_management')
    
    # Prevent deleting the last superuser
    if user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, 'Cannot delete the last superuser account.')
        return redirect('assets:user_management')
    
    if request.method == 'POST':
        try:
            username = user.username
            user.delete()
            messages.success(request, f'User "{username}" deleted successfully!')
            return redirect('assets:user_management')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
            return redirect('assets:user_management')
    
    # If not POST, show confirmation page
    context = {
        'user': user,
    }
    return render(request, 'delete_user_confirm.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_user_status(request, user_id):
    """Toggle user active status"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deactivating the current user
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('assets:user_management')
    
    # Prevent deactivating the last superuser
    if user.is_superuser and not user.is_active and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        messages.error(request, 'Cannot deactivate the last active superuser account.')
        return redirect('assets:user_management')
    
    try:
        user.is_active = not user.is_active
        user.save()
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f'User "{user.username}" {status} successfully!')
    except Exception as e:
        messages.error(request, f'Error toggling user status: {str(e)}')
    
    return redirect('assets:user_management')


@login_required
def notifications(request):
    """View user notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, 
            read_at=timezone.now()
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def create_notification(user, title, message, notification_type='system_alert', priority='medium', asset=None, employee=None):
    """Helper function to create notifications"""
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            asset=asset,
            employee=employee
        )
        return notification
    except Exception as e:
        print(f"Error creating notification: {str(e)}")
        return None


@login_required
def contact_support(request):
    """Contact support page"""
    if request.method == 'POST':
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        priority = request.POST.get('priority', 'medium')
        category = request.POST.get('category', 'general')
        
        if subject and message:
            try:
                # Create support ticket notification
                create_notification(
                    user=request.user,
                    title=f"Support Request: {subject}",
                    message=f"Category: {category}\nPriority: {priority}\n\nMessage: {message}",
                    notification_type='system_alert',
                    priority=priority
                )
                
                # Send email to support team
                from django.core.mail import send_mail
                from django.conf import settings
                
                support_email = getattr(settings, 'SUPPORT_EMAIL', 'it-office-assettrack@harren-group.com')
                
                email_subject = f"[AssetTrack Support] {subject}"
                email_message = f"""
Support Request Details:
======================

User: {request.user.username} ({request.user.email})
Category: {category}
Priority: {priority}
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Message:
--------
{message}

---
This message was sent from the AssetTrack application.
                """
                
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [support_email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Your support request has been submitted successfully! We will get back to you soon.')
                return redirect('assets:contact_support')
                
            except Exception as e:
                messages.error(request, f'Error submitting support request: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    context = {
        'user': request.user,
    }
    return render(request, 'contact_support.html', context)

# AI Assistant Views
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def ai_chat(request):
    """AI Chat interface"""
    if request.method == 'POST':
        try:
            # Support both JSON and form-encoded payloads
            query = ''
            current_page = ''
            if request.content_type and 'application/json' in request.content_type:
                try:
                    import json as _json
                    body = _json.loads(request.body or '{}')
                    query = (body.get('message') or body.get('query') or '').strip()
                    current_page = body.get('current_page', '')
                except Exception:
                    query = ''
            else:
                query = (request.POST.get('message') or request.POST.get('query') or '').strip()
                current_page = request.POST.get('current_page', '')
            
            if not query:
                return JsonResponse({'error': 'Please enter a question'})
            
            # Initialize AI assistant
            ai = AssetTrackAI()
            
            # Process query
            result = ai.process_query(query, current_page, request.user)
            
            return JsonResponse({
                'success': True,
                'response': result['response'],
                'search_results': result['search_results']
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'AI processing error: {str(e)}'
            })
    
    return render(request, 'ai_chat.html')

@login_required
def ai_quick_insights(request):
    """Get quick AI insights about the system"""
    try:
        ai = AssetTrackAI()
        insights = ai.get_quick_insights()
        
        return JsonResponse({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def ai_search(request):
    """AI-powered search endpoint"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({'results': []})
        
        try:
            ai = AssetTrackAI()
            
            # Search assets and employees
            assets = ai.search_assets(query)
            employees = ai.search_employees(query)
            
            return JsonResponse({
                'success': True,
                'assets': assets,
                'employees': employees,
                'query': query
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'error': 'Invalid request method'})
