from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from assets.models import Employee
from assets.azure_ad_integration import AzureADIntegration
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up duplicate employees and force better avatar images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Force update all employees with better avatars',
        )
        parser.add_argument(
            '--remove-duplicates',
            action='store_true',
            help='Remove duplicate employee entries',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting employee avatar cleanup...')
        )
        
        if options['remove_duplicates']:
            self.remove_duplicate_employees(options['dry_run'])
        
        if options['force_all'] or not options['remove_duplicates']:
            self.force_better_avatars(options['dry_run'])
    
    def remove_duplicate_employees(self, dry_run=False):
        """Remove duplicate employee entries"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Checking for duplicate employees...')
        
        # Find duplicates by email
        duplicates = []
        seen_emails = set()
        
        for employee in Employee.objects.all().order_by('created_at'):
            if employee.email in seen_emails:
                duplicates.append(employee)
            else:
                seen_emails.add(employee.email)
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate employees found!'))
            return
        
        self.stdout.write(f'Found {len(duplicates)} duplicate employees:')
        
        for duplicate in duplicates:
            self.stdout.write(f'  - {duplicate.name} ({duplicate.email}) - Created: {duplicate.created_at}')
            
            if not dry_run:
                # Check if this duplicate has any related data
                has_assets = duplicate.assigned_assets.exists()
                has_handovers = duplicate.handovers.exists()
                has_welcome_packs = duplicate.welcome_packs.exists()
                
                if has_assets or has_handovers or has_welcome_packs:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠️  Skipping - has related data (assets: {has_assets}, handovers: {has_handovers}, welcome_packs: {has_welcome_packs})')
                    )
                else:
                    duplicate.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'    ✓ Deleted duplicate')
                    )
            else:
                self.stdout.write(f'    [DRY RUN] Would delete duplicate')
    
    def force_better_avatars(self, dry_run=False):
        """Force better avatar images for all employees"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Forcing better avatar images...')
        
        azure_ad = AzureADIntegration()
        has_azure_config = azure_ad.get_access_token() is not None
        
        employees = Employee.objects.all()
        updated_count = 0
        azure_photo_count = 0
        placeholder_count = 0
        
        for employee in employees:
            try:
                current_avatar = employee.avatar_url
                new_avatar = None
                update_reason = ""
                
                # Try to get Azure AD photo first
                if has_azure_config and employee.azure_ad_id:
                    photo_url = azure_ad.get_user_photo_url(employee.azure_ad_id)
                    if photo_url:
                        new_avatar = photo_url
                        update_reason = "Azure AD photo"
                        azure_photo_count += 1
                
                # If no Azure AD photo, use professional placeholder
                if not new_avatar:
                    from assets.templatetags.employee_filters import get_professional_avatar_url, is_generic_avatar
                    
                    # Only update if current avatar is generic
                    if not current_avatar or is_generic_avatar(current_avatar):
                        new_avatar = get_professional_avatar_url(employee)
                        update_reason = "Professional placeholder"
                        placeholder_count += 1
                
                if new_avatar and new_avatar != current_avatar:
                    if not dry_run:
                        employee.avatar_url = new_avatar
                        employee.last_azure_sync = timezone.now()
                        employee.save()
                        updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {employee.name}: {update_reason}')
                    )
                else:
                    self.stdout.write(f'  - {employee.name}: No update needed')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {employee.name}: {str(e)}')
                )
        
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('Avatar cleanup completed!'))
        
        self.stdout.write(f'Employees updated: {updated_count}')
        self.stdout.write(f'Azure AD photos: {azure_photo_count}')
        self.stdout.write(f'Better placeholders: {placeholder_count}')
        self.stdout.write(f'Total employees processed: {employees.count()}')
