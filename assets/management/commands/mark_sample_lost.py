from django.core.management.base import BaseCommand
from assets.models import Asset
import random

class Command(BaseCommand):
    help = 'Mark some sample assets as lost for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of assets to mark as lost (default: 3)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get all available assets that are not already lost
        available_assets = Asset.objects.exclude(status='lost').exclude(status='retired')
        
        if not available_assets.exists():
            self.stdout.write(
                self.style.ERROR('No available assets found to mark as lost.')
            )
            return
        
        # Randomly select assets to mark as lost
        assets_to_mark = random.sample(list(available_assets), min(count, available_assets.count()))
        
        for asset in assets_to_mark:
            asset.status = 'lost'
            asset.save()
            self.stdout.write(
                self.style.SUCCESS(f'Marked "{asset.name}" (ID: {asset.id}) as lost')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully marked {len(assets_to_mark)} assets as lost.')
        )
        self.stdout.write(
            self.style.WARNING('You can now visit /assets/lost/ to see the lost assets.')
        )
