from django.core.management.base import BaseCommand
from assets.models import Asset

class Command(BaseCommand):
    help = 'Set default deletion permissions for existing assets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restrict-all',
            action='store_true',
            help='Restrict deletion for all assets (admin only)',
        )
        parser.add_argument(
            '--allow-deletion',
            action='store_true',
            help='Allow deletion for all assets (any user)',
        )

    def handle(self, *args, **options):
        if options['restrict_all']:
            # Set all assets to be restricted (admin only)
            Asset.objects.update(
                can_delete=False,
                deletion_restricted=True
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully restricted deletion for all {Asset.objects.count()} assets'
                )
            )
        elif options['allow_deletion']:
            # Set all assets to allow deletion
            Asset.objects.update(
                can_delete=True,
                deletion_restricted=False
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully allowed deletion for all {Asset.objects.count()} assets'
                )
            )
        else:
            # Default: restrict all assets (admin only)
            Asset.objects.update(
                can_delete=False,
                deletion_restricted=True
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set default permissions for {Asset.objects.count()} assets (admin only)'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'Use --restrict-all to restrict all assets or --allow-deletion to allow all assets'
                )
            )






