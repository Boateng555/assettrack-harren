from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from assets.models import Employee, Asset, Handover
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Create sample data for AssetTrack'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample employees
        employees_data = [
            {'name': 'John Smith', 'email': 'john.smith@company.com', 'department': 'Engineering'},
            {'name': 'Sarah Johnson', 'email': 'sarah.johnson@company.com', 'department': 'Marketing'},
            {'name': 'Mike Davis', 'email': 'mike.davis@company.com', 'department': 'Sales'},
            {'name': 'Lisa Wilson', 'email': 'lisa.wilson@company.com', 'department': 'HR'},
            {'name': 'David Brown', 'email': 'david.brown@company.com', 'department': 'Finance'},
            {'name': 'Emma Taylor', 'email': 'emma.taylor@company.com', 'department': 'IT'},
        ]
        
        employees = []
        for emp_data in employees_data:
            employee, created = Employee.objects.get_or_create(
                email=emp_data['email'],
                defaults={
                    'name': emp_data['name'],
                    'department': emp_data['department'],
                    'avatar_url': f'https://randomuser.me/api/portraits/men/{random.randint(1, 50)}.jpg'
                }
            )
            employees.append(employee)
            if created:
                self.stdout.write(f'Created employee: {employee.name}')
        
        # Create sample assets with varied purchase dates for realistic health scores
        assets_data = [
            # New assets (100% health) - Less than 1 year old
            {'name': 'MacBook Pro 16"', 'asset_type': 'laptop', 'serial_number': 'MBP001', 'model': 'MacBook Pro 16-inch', 'manufacturer': 'Apple', 'purchase_date': timezone.now().date() - timedelta(days=30)},
            {'name': 'iPhone 15 Pro', 'asset_type': 'phone', 'serial_number': 'IPH001', 'model': 'iPhone 15 Pro', 'manufacturer': 'Apple', 'purchase_date': timezone.now().date() - timedelta(days=90)},
            {'name': 'Samsung Galaxy S24', 'asset_type': 'phone', 'serial_number': 'SGS001', 'model': 'Galaxy S24', 'manufacturer': 'Samsung', 'purchase_date': timezone.now().date() - timedelta(days=180)},
            
            # 1-2 year old assets (85% health)
            {'name': 'Dell XPS 15', 'asset_type': 'laptop', 'serial_number': 'DXP001', 'model': 'XPS 15 9500', 'manufacturer': 'Dell', 'purchase_date': timezone.now().date() - timedelta(days=400)},
            {'name': 'iPad Pro 12.9"', 'asset_type': 'tablet', 'serial_number': 'IPP001', 'model': 'iPad Pro 12.9-inch', 'manufacturer': 'Apple', 'purchase_date': timezone.now().date() - timedelta(days=500)},
            {'name': 'Logitech MX Master 3', 'asset_type': 'mouse', 'serial_number': 'LMM001', 'model': 'MX Master 3', 'manufacturer': 'Logitech', 'purchase_date': timezone.now().date() - timedelta(days=600)},
            
            # 2-3 year old assets (70% health)
            {'name': 'ThinkPad X1 Carbon', 'asset_type': 'laptop', 'serial_number': 'TXC001', 'model': 'ThinkPad X1 Carbon Gen 9', 'manufacturer': 'Lenovo', 'purchase_date': timezone.now().date() - timedelta(days=800)},
            {'name': 'Dell UltraSharp 27"', 'asset_type': 'monitor', 'serial_number': 'DUM001', 'model': 'UltraSharp U2723QE', 'manufacturer': 'Dell', 'purchase_date': timezone.now().date() - timedelta(days=900)},
            
            # 3-4 year old assets (55% health)
            {'name': 'Apple Magic Keyboard', 'asset_type': 'keyboard', 'serial_number': 'AMK001', 'model': 'Magic Keyboard', 'manufacturer': 'Apple', 'purchase_date': timezone.now().date() - timedelta(days=1100)},
            
            # 4+ year old assets (40% health) - May need replacement
            {'name': 'Sony WH-1000XM5', 'asset_type': 'headphones', 'serial_number': 'SWH001', 'model': 'WH-1000XM5', 'manufacturer': 'Sony', 'purchase_date': timezone.now().date() - timedelta(days=1500)},
            
            # Additional assets with varied ages for more realistic health distribution
            {'name': 'Dell Latitude 5520', 'asset_type': 'laptop', 'serial_number': 'DLXD2D8S62', 'model': 'Latitude 5520', 'manufacturer': 'Dell', 'purchase_date': timezone.now().date() - timedelta(days=250)},
            {'name': 'boat 2020', 'asset_type': 'monitor', 'serial_number': 'DL8MJIH4le', 'model': 'Monitor 2020', 'manufacturer': 'boat', 'purchase_date': timezone.now().date() - timedelta(days=700)},
            {'name': 'Dell Latitude 2020', 'asset_type': 'keyboard', 'serial_number': 'DL8MJIH4IW', 'model': 'Latitude Keyboard 2020', 'manufacturer': 'Dell', 'purchase_date': timezone.now().date() - timedelta(days=1200)},
            {'name': 'Dell Latitude 5520', 'asset_type': 'laptop', 'serial_number': 'DL8MJIH4IB', 'model': 'Latitude 5520', 'manufacturer': 'Dell', 'purchase_date': timezone.now().date() - timedelta(days=300)},
            {'name': 'boate', 'asset_type': 'tablet', 'serial_number': '1234567890123', 'model': 'Boate Tablet', 'manufacturer': 'boate', 'purchase_date': timezone.now().date() - timedelta(days=950)},
        ]
        
        assets = []
        for asset_data in assets_data:
            asset, created = Asset.objects.get_or_create(
                serial_number=asset_data['serial_number'],
                defaults={
                    'name': asset_data['name'],
                    'asset_type': asset_data['asset_type'],
                    'model': asset_data['model'],
                    'manufacturer': asset_data['manufacturer'],
                    'purchase_date': asset_data['purchase_date'],
                    'status': 'available'
                }
            )
            # Update purchase date for existing assets too
            if not created and not asset.purchase_date:
                asset.purchase_date = asset_data['purchase_date']
                asset.save()
                self.stdout.write(f'Updated purchase date for asset: {asset.name}')
            
            assets.append(asset)
            if created:
                self.stdout.write(f'Created asset: {asset.name}')
        
        # Create sample handovers
        handover_statuses = ['Completed', 'Pending', 'In Progress', 'Pending Scan']
        handover_modes = ['Screen Sign', 'Paper & Scan']
        
        for i in range(10):
            employee = random.choice(employees)
            status = random.choice(handover_statuses)
            mode = random.choice(handover_modes)
            
            # Create handover with random date in the last 30 days
            days_ago = random.randint(0, 30)
            created_at = timezone.now() - timedelta(days=days_ago)
            
            handover = Handover.objects.create(
                employee=employee,
                mode=mode,
                status=status,
                created_by=User.objects.get(username='admin'),
                created_at=created_at
            )
            
            # Add 1-3 random assets to the handover
            handover_assets = random.sample(assets, min(3, len(assets)))
            handover.assets.set(handover_assets)
            
            self.stdout.write(f'Created handover: {handover.handover_id} for {employee.name}')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write(f'Created {len(employees)} employees, {len(assets)} assets, and 10 handovers')
