from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.models import Employee
from assets.azure_ad_integration import AzureADIntegration
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Force professional avatars for employees without Azure AD photos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--azure-only',
            action='store_true',
            help='Only update employees with Azure AD IDs',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting professional avatar enforcement...')
        )
        
        azure_ad = AzureADIntegration()
        has_azure_config = azure_ad.get_access_token() is not None
        
        # Get employees to process
        if options['azure_only']:
            employees = Employee.objects.filter(azure_ad_id__isnull=False)
            self.stdout.write(f'Processing {employees.count()} employees with Azure AD IDs...')
        else:
            employees = Employee.objects.all()
            self.stdout.write(f'Processing all {employees.count()} employees...')
        
        updated_count = 0
        azure_photo_count = 0
        professional_placeholder_count = 0
        skipped_count = 0
        
        for employee in employees:
            try:
                current_avatar = employee.avatar_url
                new_avatar = None
                update_reason = ""
                
                # For employees with Azure AD IDs, check if they have photos
                if employee.azure_ad_id and has_azure_config:
                    photo_url = azure_ad.get_user_photo_url(employee.azure_ad_id)
                    if photo_url:
                        new_avatar = photo_url
                        update_reason = "Azure AD photo"
                        azure_photo_count += 1
                    else:
                        # No Azure AD photo - force professional placeholder
                        from assets.templatetags.employee_filters import get_professional_avatar_url, is_generic_avatar
                        
                        # Always update if current avatar is generic or missing
                        if not current_avatar or is_generic_avatar(current_avatar):
                            new_avatar = get_professional_avatar_url(employee)
                            update_reason = "Professional placeholder (no Azure photo)"
                            professional_placeholder_count += 1
                        else:
                            update_reason = "Keep existing non-generic avatar"
                            skipped_count += 1
                else:
                    # For employees without Azure AD IDs, force professional placeholder if generic
                    from assets.templatetags.employee_filters import get_professional_avatar_url, is_generic_avatar
                    
                    if not current_avatar or is_generic_avatar(current_avatar):
                        new_avatar = get_professional_avatar_url(employee)
                        update_reason = "Professional placeholder (no Azure AD ID)"
                        professional_placeholder_count += 1
                    else:
                        update_reason = "Keep existing non-generic avatar"
                        skipped_count += 1
                
                if new_avatar and new_avatar != current_avatar:
                    if not options['dry_run']:
                        employee.avatar_url = new_avatar
                        employee.last_azure_sync = timezone.now()
                        employee.save()
                        updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {employee.name}: {update_reason}')
                    )
                else:
                    self.stdout.write(f'  - {employee.name}: {update_reason}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {employee.name}: {str(e)}')
                )
        
        self.stdout.write('\n' + '=' * 50)
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('Professional avatar enforcement completed!'))
        
        self.stdout.write(f'Employees updated: {updated_count}')
        self.stdout.write(f'Azure AD photos found: {azure_photo_count}')
        self.stdout.write(f'Professional placeholders applied: {professional_placeholder_count}')
        self.stdout.write(f'Skipped (already good): {skipped_count}')
        self.stdout.write(f'Total employees processed: {employees.count()}')
        
        if professional_placeholder_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ {professional_placeholder_count} employees now have professional avatars!')
            )
