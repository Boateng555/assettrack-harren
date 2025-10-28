import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import Employee, Asset
import logging

logger = logging.getLogger(__name__)

class AzureADIntegration:
    """
    Azure Active Directory integration for syncing employee data and device assignments
    """
    
    def __init__(self):
        self.tenant_id = getattr(settings, 'AZURE_TENANT_ID', None)
        self.client_id = getattr(settings, 'AZURE_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'AZURE_CLIENT_SECRET', None)
        self.access_token = None
        self.token_expires_at = None
        
    def get_access_token(self):
        """Get access token for Azure AD API"""
        if self.access_token and self.token_expires_at and timezone.now() < self.token_expires_at:
            return self.access_token
            
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            logger.error("Azure AD credentials not configured")
            return None
            
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'] - 300)  # 5 min buffer
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Azure AD access token: {e}")
            return None
    
    def get_headers(self):
        """Get headers for Azure AD API requests"""
        token = self.get_access_token()
        if not token:
            return None
            
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_users(self, include_disabled=False):
        """Get all users from Azure AD"""
        headers = self.get_headers()
        if not headers:
            return []
            
        url = "https://graph.microsoft.com/v1.0/users"
        params = {
            '$select': 'id,displayName,mail,userPrincipalName,department,jobTitle,employeeId,accountEnabled,deletedDateTime,businessPhones,mobilePhone',
            '$filter': 'accountEnabled eq true' if not include_disabled else None
        }
        
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}
        
        users = []
        
        try:
            while url:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                users.extend(data.get('value', []))
                
                # Handle pagination
                url = data.get('@odata.nextLink')
                params = {}  # Clear params for subsequent requests
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get users from Azure AD: {e}")
            return []
            
        return users
    
    def get_deleted_users(self):
        """Get recently deleted users from Azure AD (last 30 days)"""
        headers = self.get_headers()
        if not headers:
            return []
            
        url = "https://graph.microsoft.com/v1.0/directory/deletedItems/microsoft.graph.user"
        params = {
            '$select': 'id,displayName,mail,userPrincipalName,deletedDateTime'
        }
        
        deleted_users = []
        
        try:
            while url:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                deleted_users.extend(data.get('value', []))
                
                # Handle pagination
                url = data.get('@odata.nextLink')
                params = {}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get deleted users from Azure AD: {e}")
            return []
            
        return deleted_users
    
    def get_devices(self):
        """Get all devices from Azure AD"""
        headers = self.get_headers()
        if not headers:
            return []
            
        url = "https://graph.microsoft.com/v1.0/devices"
        params = {
            '$select': 'id,displayName,deviceId,manufacturer,model,operatingSystem,operatingSystemVersion,approximateLastSignInDateTime,registeredOwners,deviceCategory,deviceOwnership,registrationDateTime',
            '$filter': 'operatingSystem eq \'Windows\' or operatingSystem eq \'macOS\' or operatingSystem eq \'iOS\' or operatingSystem eq \'Android\''
        }
        
        devices = []
        
        try:
            while url:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                devices.extend(data.get('value', []))
                
                # Handle pagination
                url = data.get('@odata.nextLink')
                params = {}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get devices from Azure AD: {e}")
            return []
            
        return devices
    
    def get_user_devices(self, user_id):
        """Get devices assigned to a specific user"""
        headers = self.get_headers()
        if not headers:
            return []
            
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/registeredDevices"
        params = {
            '$select': 'id,displayName,deviceId,manufacturer,model,operatingSystem,operatingSystemVersion'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('value', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get devices for user {user_id}: {e}")
            return []
    
    def get_user_photo_url(self, user_id):
        """Get user's profile photo URL from Azure AD"""
        headers = self.get_headers()
        if not headers:
            return None
            
        # Check if user has a photo
        photo_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/photo"
        
        try:
            response = requests.get(photo_url, headers=headers)
            if response.status_code == 200:
                # User has a photo, return the URL
                return f"https://graph.microsoft.com/v1.0/users/{user_id}/photo/$value"
            elif response.status_code == 404:
                # User doesn't have a photo
                logger.debug(f"No photo found for user {user_id}")
                return None
            else:
                logger.warning(f"Unexpected status code {response.status_code} when checking photo for user {user_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check photo for user {user_id}: {e}")
            return None
    
    def get_user_photo_data(self, user_id):
        """Get user's profile photo data (binary) from Azure AD"""
        headers = self.get_headers()
        if not headers:
            return None
            
        photo_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/photo/$value"
        
        try:
            response = requests.get(photo_url, headers=headers)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:
                logger.debug(f"No photo found for user {user_id}")
                return None
            else:
                logger.warning(f"Unexpected status code {response.status_code} when getting photo for user {user_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get photo for user {user_id}: {e}")
            return None
    
    def sync_employees_with_devices(self):
        """Sync employees from Azure AD with their devices automatically assigned"""
        azure_users = self.get_users()
        azure_deleted_users = self.get_deleted_users()
        
        # Get all local employees with Azure AD IDs
        local_employees = Employee.objects.filter(azure_ad_id__isnull=False)
        
        # Create sets for comparison
        azure_user_ids = {user['id'] for user in azure_users}
        azure_deleted_user_ids = {user['id'] for user in azure_deleted_users}
        local_azure_ids = {emp.azure_ad_id for emp in local_employees}
        
        synced_count = 0
        updated_count = 0
        disabled_count = 0
        deleted_count = 0
        devices_synced = 0
        devices_assigned = 0
        
        # Process active Azure users
        for user in azure_users:
            try:
                # Map Azure AD user to Employee model
                email = user.get('mail', '')
                if not email:
                    email = user.get('userPrincipalName', '')
                
                department = user.get('department', '')
                if not department:
                    # Check if user has @harren-group.com email (internal user)
                    if email.endswith('@harren-group.com'):
                        department = 'Internal'  # Default internal users to Internal department
                    else:
                        department = 'External'
                
                # Get user's profile photo URL
                photo_url = self.get_user_photo_url(user.get('id'))
                
                # Get phone number from Azure AD (business phone or mobile phone)
                phone = ''
                business_phones = user.get('businessPhones', [])
                mobile_phone = user.get('mobilePhone', '')
                
                if business_phones and len(business_phones) > 0:
                    phone = business_phones[0]  # Use first business phone
                elif mobile_phone:
                    phone = mobile_phone
                
                # Detect office location based on phone number and department
                office_location = 'bernem'  # Default
                if phone:
                    from .views import detect_office_by_phone_and_department
                    detected_office = detect_office_by_phone_and_department(phone, department)
                    if detected_office:
                        office_location = detected_office
                
                employee_data = {
                    'name': user.get('displayName', ''),
                    'email': email,
                    'department': department,
                    'azure_ad_id': user.get('id'),
                    'azure_ad_username': user.get('userPrincipalName', ''),
                    'job_title': user.get('jobTitle', ''),
                    'employee_id': user.get('employeeId', ''),
                    'phone': phone,
                    'office_location': office_location,
                    'last_azure_sync': timezone.now(),
                }
                
                # Add photo URL if available, otherwise use professional placeholder
                if photo_url:
                    employee_data['avatar_url'] = photo_url
                else:
                    # Always use professional placeholder when no Azure AD photo is available
                    from assets.templatetags.employee_filters import get_professional_avatar_url, is_generic_avatar
                    
                    # Create a mock employee object for the placeholder function
                    class MockEmployee:
                        def __init__(self, name):
                            self.name = name
                    
                    mock_employee = MockEmployee(employee_data['name'])
                    employee_data['avatar_url'] = get_professional_avatar_url(mock_employee)
                
                # Check if employee already exists
                existing_employee = None
                if employee_data['azure_ad_id']:
                    existing_employee = Employee.objects.filter(azure_ad_id=employee_data['azure_ad_id']).first()
                
                if not existing_employee and employee_data['email']:
                    existing_employee = Employee.objects.filter(email=employee_data['email']).first()
                
                if existing_employee:
                    # Update existing employee
                    for field, value in employee_data.items():
                        if hasattr(existing_employee, field) and value:
                            setattr(existing_employee, field, value)
                    existing_employee.save()
                    updated_count += 1
                    employee = existing_employee
                else:
                    # Create new employee
                    employee = Employee.objects.create(**employee_data)
                    synced_count += 1
                
                # Sync devices for this employee
                user_devices = self.get_user_devices(user.get('id'))
                for device in user_devices:
                    try:
                        # Determine asset type based on operating system
                        os_type = device.get('operatingSystem', '')
                        if os_type in ['Windows', 'macOS']:
                            asset_type = 'laptop'
                        elif os_type in ['iOS', 'Android']:
                            asset_type = 'phone'
                        else:
                            asset_type = 'other'
                        
                        # Create asset data
                        asset_data = {
                            'name': device.get('displayName', f"{employee.name}'s {asset_type.title()}"),
                            'asset_type': asset_type,
                            'serial_number': device.get('deviceId', f"AZURE_{device.get('id', '')}"),
                            'model': device.get('model', ''),
                            'manufacturer': device.get('manufacturer', ''),
                            'azure_ad_id': device.get('id'),
                            'operating_system': device.get('operatingSystem', ''),
                            'os_version': device.get('operatingSystemVersion', ''),
                            'status': 'assigned',
                            'assigned_to': employee,
                            'last_azure_sync': timezone.now(),
                        }
                        
                        # Store Azure AD last sign-in date if available
                        if device.get('approximateLastSignInDateTime'):
                            try:
                                from datetime import datetime
                                signin_date = datetime.fromisoformat(device['approximateLastSignInDateTime'].replace('Z', '+00:00'))
                                asset_data['azure_last_signin'] = signin_date
                            except (ValueError, TypeError):
                                pass  # Skip if date format is invalid
                        
                        # Set purchase_date to first Azure sync date if not already set
                        # This ensures health calculations use the correct date
                        if not asset_data.get('purchase_date'):
                            asset_data['purchase_date'] = timezone.now().date()
                        
                        # Check if asset already exists
                        existing_asset = None
                        if asset_data['azure_ad_id']:
                            existing_asset = Asset.objects.filter(azure_ad_id=asset_data['azure_ad_id']).first()
                        elif asset_data['serial_number']:
                            existing_asset = Asset.objects.filter(serial_number=asset_data['serial_number']).first()
                        
                        if existing_asset:
                            # Update existing asset
                            for field, value in asset_data.items():
                                if hasattr(existing_asset, field) and value:
                                    setattr(existing_asset, field, value)
                            existing_asset.save()
                        else:
                            # Create new asset
                            Asset.objects.create(**asset_data)
                            devices_synced += 1
                        
                        devices_assigned += 1
                        
                    except Exception as e:
                        logger.error(f"Error syncing device {device.get('displayName', 'Unknown')} for employee {employee.name}: {e}")
                        continue
                    
            except Exception as e:
                logger.error(f"Error syncing employee {user.get('displayName', 'Unknown')}: {e}")
                continue
        
        # Handle disabled users (users that exist locally but not in active Azure users)
        disabled_local_ids = local_azure_ids - azure_user_ids - azure_deleted_user_ids
        for azure_id in disabled_local_ids:
            try:
                employee = Employee.objects.filter(azure_ad_id=azure_id).first()
                if employee:
                    # Mark as disabled but don't delete
                    employee.status = 'inactive'
                    employee.last_azure_sync = timezone.now()
                    employee.save()
                    disabled_count += 1
                    logger.info(f"Marked employee {employee.name} as inactive (disabled in Azure AD)")
            except Exception as e:
                logger.error(f"Error handling disabled employee with Azure ID {azure_id}: {e}")
        
        # Handle deleted users
        for deleted_user in azure_deleted_users:
            try:
                azure_id = deleted_user.get('id')
                employee = Employee.objects.filter(azure_ad_id=azure_id).first()
                if employee:
                    # Mark as deleted but don't physically delete
                    employee.status = 'deleted'
                    employee.last_azure_sync = timezone.now()
                    employee.save()
                    deleted_count += 1
                    logger.info(f"Marked employee {employee.name} as deleted (deleted in Azure AD)")
            except Exception as e:
                logger.error(f"Error handling deleted employee {deleted_user.get('displayName', 'Unknown')}: {e}")
        
        logger.info(f"Azure AD sync completed: {synced_count} new, {updated_count} updated, {disabled_count} disabled, {deleted_count} deleted, {devices_synced} devices synced, {devices_assigned} devices assigned")
        return synced_count, updated_count, disabled_count, deleted_count, devices_synced, devices_assigned
    
    def sync_employees_with_changes(self):
        """Legacy sync method - now calls the enhanced version with devices"""
        return self.sync_employees_with_devices()
    
    def sync_devices(self):
        """Sync devices from Azure AD to local database"""
        devices = self.get_devices()
        synced_count = 0
        updated_count = 0
        
        for device in devices:
            try:
                # Map Azure AD device to Asset model
                os_type = device.get('operatingSystem', '')
                if os_type in ['Windows', 'macOS']:
                    asset_type = 'laptop'
                elif os_type in ['iOS', 'Android']:
                    asset_type = 'phone'
                else:
                    asset_type = 'other'
                
                asset_data = {
                    'name': device.get('displayName', ''),
                    'asset_type': asset_type,
                    'serial_number': device.get('deviceId', ''),
                    'model': device.get('model', ''),
                    'manufacturer': device.get('manufacturer', ''),
                    'azure_ad_id': device.get('id'),
                    'operating_system': device.get('operatingSystem', ''),
                    'os_version': device.get('operatingSystemVersion', ''),
                }
                
                # Store Azure AD last sign-in date if available
                if device.get('approximateLastSignInDateTime'):
                    try:
                        from datetime import datetime
                        signin_date = datetime.fromisoformat(device['approximateLastSignInDateTime'].replace('Z', '+00:00'))
                        asset_data['azure_last_signin'] = signin_date
                    except (ValueError, TypeError):
                        pass  # Skip if date format is invalid
                
                # Store Azure AD registration date if available
                if device.get('registrationDateTime'):
                    try:
                        from datetime import datetime
                        registration_date = datetime.fromisoformat(device['registrationDateTime'].replace('Z', '+00:00'))
                        asset_data['azure_registration_date'] = registration_date
                    except (ValueError, TypeError):
                        pass  # Skip if date format is invalid
                
                # Set purchase_date to Azure AD registration date if available, otherwise sync date
                if not asset_data.get('purchase_date'):
                    if asset_data.get('azure_registration_date'):
                        # Use the actual Azure AD registration date as purchase date
                        asset_data['purchase_date'] = asset_data['azure_registration_date'].date()
                    else:
                        # Fallback to current sync date if no registration date available
                        asset_data['purchase_date'] = timezone.now().date()
                
                # Check if asset already exists
                existing_asset = None
                if asset_data['azure_ad_id']:
                    existing_asset = Asset.objects.filter(azure_ad_id=asset_data['azure_ad_id']).first()
                elif asset_data['serial_number']:
                    existing_asset = Asset.objects.filter(serial_number=asset_data['serial_number']).first()
                
                if existing_asset:
                    # Update existing asset
                    for field, value in asset_data.items():
                        if hasattr(existing_asset, field) and value:
                            setattr(existing_asset, field, value)
                    existing_asset.save()
                    updated_count += 1
                else:
                    # Create new asset
                    Asset.objects.create(**asset_data)
                    synced_count += 1
                    
            except Exception as e:
                logger.error(f"Error syncing device {device.get('displayName', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Azure AD device sync completed: {synced_count} new devices, {updated_count} updated")
        return synced_count, updated_count
    
    def sync_device_assignments(self):
        """Sync device assignments from Azure AD"""
        users = self.get_users()
        assignment_count = 0
        
        for user in users:
            try:
                user_id = user.get('id')
                if not user_id:
                    continue
                
                # Get devices assigned to this user
                user_devices = self.get_user_devices(user_id)
                
                # Find the employee
                employee = Employee.objects.filter(azure_ad_id=user_id).first()
                if not employee:
                    continue
                
                # Update device assignments
                for device in user_devices:
                    asset = Asset.objects.filter(azure_ad_id=device.get('id')).first()
                    if asset and asset.assigned_to != employee:
                        asset.assigned_to = employee
                        asset.status = 'assigned'
                        asset.save()
                        assignment_count += 1
                        
            except Exception as e:
                logger.error(f"Error syncing device assignments for user {user.get('displayName', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Azure AD device assignment sync completed: {assignment_count} assignments updated")
        return assignment_count
    
    def cleanup_orphaned_assets(self):
        """Clean up assets that are no longer assigned to active employees"""
        # Get all assets assigned to inactive/deleted employees
        orphaned_assets = Asset.objects.filter(
            assigned_to__status__in=['inactive', 'deleted']
        )
        
        cleanup_count = 0
        for asset in orphaned_assets:
            asset.assigned_to = None
            asset.status = 'available'
            asset.save()
            cleanup_count += 1
            logger.info(f"Unassigned asset {asset.name} from inactive employee {asset.assigned_to.name if asset.assigned_to else 'Unknown'}")
        
        logger.info(f"Cleanup completed: {cleanup_count} assets unassigned from inactive employees")
        return cleanup_count
    
    def get_sync_summary(self):
        """Get a summary of the current sync status"""
        total_azure_users = len(self.get_users())
        total_local_employees = Employee.objects.count()
        total_azure_employees = Employee.objects.filter(azure_ad_id__isnull=False).count()
        active_employees = Employee.objects.filter(status='active').count()
        inactive_employees = Employee.objects.filter(status='inactive').count()
        deleted_employees = Employee.objects.filter(status='deleted').count()
        
        return {
            'azure_users': total_azure_users,
            'local_employees': total_local_employees,
            'azure_synced_employees': total_azure_employees,
            'active_employees': active_employees,
            'inactive_employees': inactive_employees,
            'deleted_employees': deleted_employees,
            'last_sync': timezone.now()
        }
    
    def full_sync(self):
        """Perform full sync of employees, devices, and assignments with change detection"""
        logger.info("Starting full Azure AD sync with change detection...")
        
        # Sync employees with full change detection and devices
        employee_synced, employee_updated, employee_disabled, employee_deleted, devices_synced, devices_assigned = self.sync_employees_with_devices()
        
        # Sync additional devices (standalone devices not assigned to users)
        device_synced, device_updated = self.sync_devices()
        
        # Sync device assignments
        assignments_updated = self.sync_device_assignments()
        
        # Clean up orphaned assets
        cleanup_count = self.cleanup_orphaned_assets()
        
        logger.info(f"Full Azure AD sync completed: "
                   f"{employee_synced} new employees, {employee_updated} updated employees, "
                   f"{employee_disabled} disabled employees, {employee_deleted} deleted employees, "
                   f"{devices_synced} user devices synced, {devices_assigned} devices assigned, "
                   f"{device_synced} standalone devices synced, {device_updated} standalone devices updated, "
                   f"{assignments_updated} device assignments updated, "
                   f"{cleanup_count} assets cleaned up")
        
        return {
            'employees_synced': employee_synced,
            'employees_updated': employee_updated,
            'employees_disabled': employee_disabled,
            'employees_deleted': employee_deleted,
            'user_devices_synced': devices_synced,
            'user_devices_assigned': devices_assigned,
            'standalone_devices_synced': device_synced,
            'standalone_devices_updated': device_updated,
            'assignments_updated': assignments_updated,
            'assets_cleaned_up': cleanup_count
        }
