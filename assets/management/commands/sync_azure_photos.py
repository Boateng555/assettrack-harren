from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.models import Employee
from assets.azure_ad_integration import AzureADIntegration
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync Azure AD profile photos for existing employees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all employees, even if they already have photos',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Sync photos for a specific employee ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Azure AD photo sync...')
        )
        
        azure_ad = AzureADIntegration()
        
        # Check if Azure AD is configured
        if not azure_ad.get_access_token():
            self.stdout.write(
                self.style.ERROR('Azure AD not configured. Please check your settings.')
            )
            return
        
        # Get employees to sync
        if options['employee_id']:
            employees = Employee.objects.filter(id=options['employee_id'])
            if not employees.exists():
                self.stdout.write(
                    self.style.ERROR(f'Employee with ID {options["employee_id"]} not found.')
                )
                return
        else:
            if options['force']:
                employees = Employee.objects.filter(azure_ad_id__isnull=False)
            else:
                # Only sync employees without photos or with placeholder photos
                employees = Employee.objects.filter(
                    azure_ad_id__isnull=False
                ).exclude(
                    avatar_url__icontains='randomuser.me'
                )
        
        self.stdout.write(f'Found {employees.count()} employees to sync...')
        
        synced_count = 0
        error_count = 0
        
        for employee in employees:
            try:
                self.stdout.write(f'Processing {employee.name}...')
                
                # Get photo URL from Azure AD
                photo_url = azure_ad.get_user_photo_url(employee.azure_ad_id)
                
                if photo_url:
                    # Update employee with photo URL
                    employee.avatar_url = photo_url
                    employee.last_azure_sync = timezone.now()
                    employee.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Photo synced for {employee.name}')
                    )
                    synced_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  - No photo found for {employee.name}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error syncing {employee.name}: {str(e)}')
                )
                error_count += 1
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Azure AD photo sync completed!')
        )
        self.stdout.write(f'Successfully synced: {synced_count}')
        self.stdout.write(f'Errors: {error_count}')
        self.stdout.write(f'Total processed: {employees.count()}')
