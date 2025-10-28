from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.models import Asset
from assets.views import calculate_health_score


class Command(BaseCommand):
    help = 'Recalculate health scores for all assets using registration date instead of activity date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--azure-only',
            action='store_true',
            help='Only recalculate health scores for Azure AD assets',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        azure_only = options['azure_only']
        
        # Get assets to update
        if azure_only:
            assets = Asset.objects.filter(azure_ad_id__isnull=False)
            self.stdout.write(f"Found {assets.count()} Azure AD assets to process")
        else:
            assets = Asset.objects.all()
            self.stdout.write(f"Found {assets.count()} total assets to process")
        
        updated_count = 0
        azure_updated_count = 0
        
        for asset in assets:
            old_health_score = asset.health_score
            new_health_score = calculate_health_score(asset)
            
            # Show what would change
            if old_health_score != new_health_score:
                self.stdout.write(
                    f"Asset '{asset.name}' (ID: {asset.id}): "
                    f"Health score {old_health_score}% → {new_health_score}%"
                )
                
                if asset.azure_ad_id:
                    self.stdout.write(
                        f"  Azure AD ID: {asset.azure_ad_id}"
                    )
                    if asset.azure_registration_date:
                        self.stdout.write(
                            f"  Azure AD Registration Date: {asset.azure_registration_date.date()}"
                        )
                    elif asset.last_azure_sync:
                        self.stdout.write(
                            f"  Sync Date (fallback): {asset.last_azure_sync.date()}"
                        )
                    if asset.azure_last_signin:
                        self.stdout.write(
                            f"  Last Activity: {asset.azure_last_signin.date()}"
                        )
                    self.stdout.write(
                        f"  Using Azure AD Registration Date for Health Calculation"
                    )
                
                if not dry_run:
                    asset.health_score = new_health_score
                    asset.save(update_fields=['health_score'])
                
                updated_count += 1
                if asset.azure_ad_id:
                    azure_updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN: Would update {updated_count} assets "
                    f"({azure_updated_count} Azure AD assets)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully updated {updated_count} assets "
                    f"({azure_updated_count} Azure AD assets)"
                )
            )
            
            if azure_only:
                self.stdout.write(
                    self.style.SUCCESS(
                        "All Azure AD assets now use registration date for health calculation"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "All assets now use registration date for health calculation"
                    )
                )
