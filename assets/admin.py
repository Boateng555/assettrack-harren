from django.contrib import admin
from .models import Employee, Asset, Handover, HandoverAsset, WelcomePack, EmailSettings

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'department', 'office_location', 'is_active', 'created_at']
    list_filter = ['department', 'office_location', 'is_active', 'created_at']
    search_fields = ['name', 'email']
    ordering = ['name']

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_type', 'serial_number', 'st_tag', 'status', 'assigned_to', 'can_delete', 'deletion_restricted', 'created_at']
    list_filter = ['asset_type', 'status', 'can_delete', 'deletion_restricted', 'created_at']
    search_fields = ['name', 'serial_number', 'st_tag', 'model']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'asset_type', 'serial_number', 'st_tag', 'model', 'manufacturer', 'status', 'assigned_to')
        }),
        ('Dates', {
            'fields': ('purchase_date', 'warranty_expiry', 'subscription_end')
        }),
        ('Software Details', {
            'fields': ('license_key', 'license_type', 'version', 'vendor', 'seats', 'used_seats'),
            'classes': ('collapse',)
        }),
        ('Maintenance Information', {
            'fields': ('maintenance_start_date', 'maintenance_expected_end', 'maintenance_notes'),
            'classes': ('collapse',)
        }),
        ('Azure AD Integration', {
            'fields': ('azure_ad_id', 'operating_system', 'os_version', 'last_azure_sync'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('can_delete', 'deletion_restricted'),
            'description': 'Control who can delete this asset'
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

@admin.register(Handover)
class HandoverAdmin(admin.ModelAdmin):
    list_display = ['handover_id', 'employee', 'mode', 'status', 'created_at', 'completed_at']
    list_filter = ['mode', 'status', 'created_at']
    search_fields = ['handover_id', 'employee__name']
    ordering = ['-created_at']
    readonly_fields = ['handover_id', 'created_at', 'updated_at']

@admin.register(HandoverAsset)
class HandoverAssetAdmin(admin.ModelAdmin):
    list_display = ['handover', 'asset', 'condition_before', 'condition_after']
    list_filter = ['handover__status']
    search_fields = ['handover__handover_id', 'asset__name']

@admin.register(WelcomePack)
class WelcomePackAdmin(admin.ModelAdmin):
    list_display = ['employee', 'employee_email', 'it_contact_person', 'is_active', 'generated_at', 'generated_by']
    list_filter = ['is_active', 'generated_at', 'email_sent_to_employee', 'email_sent_to_it']
    search_fields = ['employee__name', 'employee_email', 'it_contact_person']
    ordering = ['-generated_at']
    readonly_fields = ['generated_at', 'email_sent_at']

@admin.register(EmailSettings)
class EmailSettingsAdmin(admin.ModelAdmin):
    list_display = ['email_backend', 'from_email', 'from_name', 'is_active', 'updated_at']
    list_filter = ['email_backend', 'is_active', 'created_at']
    search_fields = ['from_email', 'from_name', 'company_name']
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('email_backend', 'is_active', 'from_email', 'from_name', 'company_name', 'email_domain')
        }),
        ('SMTP Settings', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'use_tls'),
        }),
    )
