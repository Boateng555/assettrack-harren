from django import template
from django.urls import reverse
from assets.models import Employee
from datetime import date

register = template.Library()

def is_valid_avatar_url(url):
    """Check if an avatar URL is valid and not empty"""
    return url and isinstance(url, str) and len(url.strip()) > 0

@register.filter
def employee_avatar_url(employee):
    """
    Get the appropriate avatar URL for an employee.
    Uses consistent gray person icons everywhere.
    """
    if not employee:
        return get_professional_avatar_url(employee)
    
    # Priority 1: Use stored avatar URL (gray person icon)
    if employee.avatar_url and is_valid_avatar_url(employee.avatar_url):
        return employee.avatar_url
    
    # Priority 2: Fall back to gray person icon
    return get_professional_avatar_url(employee)

def get_better_placeholder_url(employee):
    """
    Generate a better placeholder URL based on employee name.
    Uses DiceBear API for professional, clean avatars with initials.
    """
    if not employee or not employee.name:
        return "https://api.dicebear.com/7.x/initials/svg?seed=default&backgroundColor=6b7280&textColor=ffffff&fontSize=40"
    
    # Clean the name for use as seed
    seed = employee.name.lower().replace(' ', '').replace('.', '').replace('-', '')
    
    # Extract initials (first letter of first and last name)
    name_parts = employee.name.strip().split()
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    else:
        initials = employee.name[:2].upper()
    
    # Use DiceBear initials style for clean, professional look
    # Similar to the generic user icon with checkmark style
    return f"https://api.dicebear.com/7.x/initials/svg?seed={seed}&backgroundColor=6b7280&textColor=ffffff&fontSize=40&text={initials}"

def get_professional_avatar_url(employee):
    """
    Generate a gray person avatar URL for an employee.
    Uses a consistent gray person icon everywhere.
    """
    if not employee or not employee.name:
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIxNiIgcj0iNiIgZmlsbD0iIzY2NjY2NiIvPgo8cGF0aCBkPSJNMTAgMzJDMTAgMjcuNTgyIDEzLjU4MiAyNCAxOCAyNEgyMkMyNi40MTggMjQgMzAgMjcuNTgyIDMwIDMyVjM0SDEwVjMyWiIgZmlsbD0iIzY2NjY2NiIvPgo8L3N2Zz4K"
    
    # Use gray person icon for all employees - consistent everywhere
    return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIxNiIgcj0iNiIgZmlsbD0iIzY2NjY2NiIvPgo8cGF0aCBkPSJNMTAgMzJDMTAgMjcuNTgyIDEzLjU4MiAyNCAxOCAyNEgyMkMyNi40MTggMjQgMzAgMjcuNTgyIDMwIDMyVjM0SDEwVjMyWiIgZmlsbD0iIzY2NjY2NiIvPgo8L3N2Zz4K"

def is_generic_avatar(avatar_url):
    """
    Check if the avatar URL is a generic/placeholder that should be replaced.
    """
    if not avatar_url:
        return True
    
    # Check for various generic avatar patterns
    generic_patterns = [
        'randomuser.me',
        'ui-avatars.com',
        'gravatar.com/avatar/',
        'placeholder.com',
        'dummyimage.com',
        'unsplash.com/photo-1472099645785-5658abf4ff4e'  # Add the hardcoded admin avatar
    ]
    
    return any(pattern in avatar_url.lower() for pattern in generic_patterns)

@register.filter
def user_avatar_url(user):
    """
    Get the appropriate avatar URL for a Django User.
    Always returns a working, professional avatar URL.
    """
    if not user:
        return get_professional_avatar_url_for_user(user)
    
    # Check if user has an associated employee record
    try:
        employee = user.employee
        if employee:
            return employee_avatar_url(employee)
    except Employee.DoesNotExist:
        pass
    
    # For admin users without employee records, use their username/name
    return get_professional_avatar_url_for_user(user)

def get_professional_avatar_url_for_user(user):
    """
    Generate a professional avatar URL for Django User objects.
    """
    if not user:
        return "https://api.dicebear.com/7.x/initials/svg?seed=default&backgroundColor=1e40af&textColor=ffffff&fontSize=40&fontWeight=500&radius=50"
    
    # Use full name if available, otherwise username
    display_name = user.get_full_name() if user.get_full_name() else user.username
    
    # Clean the name for use as seed
    seed = display_name.lower().replace(' ', '').replace('.', '').replace('-', '')
    
    # Extract initials (first letter of first and last name)
    name_parts = display_name.strip().split()
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    else:
        initials = display_name[:2].upper()
    
    # Dark blue background with white text - matches the reference image exactly
    return f"https://api.dicebear.com/7.x/initials/svg?seed={seed}&backgroundColor=1e40af&textColor=ffffff&fontSize=40&fontWeight=500&radius=50&text={initials}"

@register.filter
def safe_employee_avatar_url(employee):
    """
    Get a safe avatar URL for an employee with error handling.
    Uses consistent gray person icons everywhere.
    """
    try:
        # Priority 1: Use stored avatar URL (gray person icon)
        if employee and employee.avatar_url and is_valid_avatar_url(employee.avatar_url):
            return employee.avatar_url
        
        # Priority 2: Fall back to gray person icon
        return get_professional_avatar_url(employee)
    except Exception:
        # If anything goes wrong, return a guaranteed working avatar with initials
        if employee and employee.name:
            # Use the same improved logic as get_professional_avatar_url
            seed = employee.name.lower().replace(' ', '').replace('.', '').replace('-', '').replace('_', '')
            
            # Extract initials (first letter of first and last name)
            name_parts = employee.name.strip().split()
            if len(name_parts) >= 2:
                # Get first letter of first name and last name
                first_initial = name_parts[0][0].upper() if name_parts[0] else ''
                last_initial = name_parts[-1][0].upper() if name_parts[-1] else ''
                initials = first_initial + last_initial
            else:
                # Single name - use first two letters
                initials = employee.name[:2].upper()
            
            # Ensure initials are valid (only letters, 2 characters max)
            initials = ''.join(c for c in initials if c.isalpha())[:2]
            
            # If no valid initials, use first two letters of the name
            if not initials:
                initials = ''.join(c for c in employee.name if c.isalpha())[:2].upper()
            
            # Special case: if initials are "US" and it's a generic pattern, try to get better initials
            if initials == "US" and ("user" in employee.name.lower() or "test" in employee.name.lower()):
                # Try to get initials from the first two words
                words = [word for word in employee.name.split() if word.isalpha()]
                if len(words) >= 2:
                    initials = (words[0][0] + words[1][0]).upper()
                elif len(words) == 1 and len(words[0]) >= 2:
                    initials = words[0][:2].upper()
            
            # Final fallback
            if not initials or initials == "US":
                initials = 'U'  # Single 'U' for User
            
            return f"https://api.dicebear.com/7.x/initials/svg?seed={seed}&backgroundColor=1e40af&textColor=ffffff&fontSize=40&fontWeight=500&radius=50&text={initials}"
        else:
            return "https://api.dicebear.com/7.x/initials/svg?seed=user&backgroundColor=1e40af&textColor=ffffff&fontSize=40&fontWeight=500&radius=50&text=U"

@register.filter
def safe_user_avatar_url(user):
    """
    Get a safe avatar URL for a Django User with error handling.
    Always returns a working, professional avatar URL.
    """
    try:
        return user_avatar_url(user)
    except Exception:
        # If anything goes wrong, return a guaranteed working avatar
        return "https://api.dicebear.com/7.x/initials/svg?seed=user&backgroundColor=1e40af&textColor=ffffff&fontSize=40&fontWeight=500&radius=50&text=U"

@register.filter
def health_reference_date(asset):
    """
    Get the reference date used for health calculations.
    For Azure AD assets, uses the actual Azure AD registration date.
    For manual assets, uses purchase_date.
    """
    if not asset:
        return None
    
    # For Azure AD assets, use the actual Azure AD registration date
    if asset.azure_ad_id and asset.azure_registration_date:
        # Asset came from Azure AD - use the actual registration date from Azure AD
        return asset.azure_registration_date.date()
    elif asset.azure_ad_id and asset.last_azure_sync:
        # Fallback to sync date if registration date not available
        return asset.last_azure_sync.date()
    elif asset.purchase_date:
        # Manually added asset - use purchase date
        return asset.purchase_date
    elif asset.last_azure_sync:
        # Fallback to Azure sync date if no other date available
        return asset.last_azure_sync.date()
    else:
        return None
