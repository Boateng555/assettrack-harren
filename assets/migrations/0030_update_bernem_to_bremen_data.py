# Generated manually to fix data

from django.db import migrations

def update_bernem_to_bremen(apps, schema_editor):
    """Update all 'bernem' office_location values to 'bremen'"""
    Asset = apps.get_model('assets', 'Asset')
    Employee = apps.get_model('assets', 'Employee')
    
    # Update Asset records
    Asset.objects.filter(office_location='bernem').update(office_location='bremen')
    
    # Update Employee records
    Employee.objects.filter(office_location='bernem').update(office_location='bremen')
    
    print("Updated all 'bernem' office_location values to 'bremen'")

def reverse_update_bernem_to_bremen(apps, schema_editor):
    """Reverse the update - change 'bremen' back to 'bernem'"""
    Asset = apps.get_model('assets', 'Asset')
    Employee = apps.get_model('assets', 'Employee')
    
    # Update Asset records
    Asset.objects.filter(office_location='bremen').update(office_location='bernem')
    
    # Update Employee records
    Employee.objects.filter(office_location='bremen').update(office_location='bernem')
    
    print("Reversed update - changed 'bremen' back to 'bernem'")

class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0029_fix_bernem_to_bremen'),
    ]

    operations = [
        migrations.RunPython(update_bernem_to_bremen, reverse_update_bernem_to_bremen),
    ]
