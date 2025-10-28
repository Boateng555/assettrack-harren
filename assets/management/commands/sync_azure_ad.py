from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.azure_ad_integration import AzureADIntegration
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync employees and devices from Azure Active Directory with full change detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--employees-only',
            action='store_true',
            help='Sync only employees from Azure AD',
        )
        parser.add_argument(
            '--devices-only',
            action='store_true',
            help='Sync only devices from Azure AD',
        )
        parser.add_argument(
            '--assignments-only',
            action='store_true',
            help='Sync only device assignments from Azure AD',
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show sync summary without performing sync',
        )
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Only cleanup orphaned assets',
        )

    def handle(self, *args, **options):
        azure_ad = AzureADIntegration()
        
        if options['summary']:
            self.show_sync_summary(azure_ad)
            return
            
        if options['cleanup_only']:
            self.stdout.write('Cleaning up orphaned assets...')
            cleanup_count = azure_ad.cleanup_orphaned_assets()
            self.stdout.write(
                self.style.SUCCESS(f'Cleanup completed: {cleanup_count} assets unassigned')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('Starting Azure AD sync with change detection...'))
        
        if options['employees_only']:
            self.stdout.write('Syncing employees with change detection and devices...')
            synced, updated, disabled, deleted, devices_synced, devices_assigned = azure_ad.sync_employees_with_devices()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Employee sync completed:\n'
                    f'  - New: {synced}\n'
                    f'  - Updated: {updated}\n'
                    f'  - Disabled: {disabled}\n'
                    f'  - Deleted: {deleted}\n'
                    f'  - Devices synced: {devices_synced}\n'
                    f'  - Devices assigned: {devices_assigned}'
                )
            )
            
        elif options['devices_only']:
            self.stdout.write('Syncing devices only...')
            synced, updated = azure_ad.sync_devices()
            self.stdout.write(
                self.style.SUCCESS(f'Device sync completed: {synced} new, {updated} updated')
            )
            
        elif options['assignments_only']:
            self.stdout.write('Syncing device assignments only...')
            assignments = azure_ad.sync_device_assignments()
            self.stdout.write(
                self.style.SUCCESS(f'Device assignment sync completed: {assignments} assignments updated')
            )
            
        else:
            self.stdout.write('Performing full sync with change detection...')
            results = azure_ad.full_sync()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Full Azure AD sync completed:\n'
                    f'  - Employees: {results["employees_synced"]} new, {results["employees_updated"]} updated, {results["employees_disabled"]} disabled, {results["employees_deleted"]} deleted\n'
                    f'  - User Devices: {results["user_devices_synced"]} synced, {results["user_devices_assigned"]} assigned\n'
                    f'  - Standalone Devices: {results["standalone_devices_synced"]} synced, {results["standalone_devices_updated"]} updated\n'
                    f'  - Assignments: {results["assignments_updated"]} updated\n'
                    f'  - Assets cleaned up: {results["assets_cleaned_up"]}'
                )
            )
    
    def show_sync_summary(self, azure_ad):
        """Show a summary of the current sync status"""
        summary = azure_ad.get_sync_summary()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Azure AD Sync Summary:\n'
                f'  - Azure AD Users: {summary["azure_users"]}\n'
                f'  - Local Employees: {summary["local_employees"]}\n'
                f'  - Azure Synced Employees: {summary["azure_synced_employees"]}\n'
                f'  - Active Employees: {summary["active_employees"]}\n'
                f'  - Inactive Employees: {summary["inactive_employees"]}\n'
                f'  - Deleted Employees: {summary["deleted_employees"]}\n'
                f'  - Last Sync: {summary["last_sync"]}'
            )
        )







