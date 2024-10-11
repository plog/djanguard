from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ('name', 'email', 'short_message', 'timestamp','ip_address')  # Display the custom short message
    search_fields = ('name', 'email')  # Add search functionality
    list_filter   = ('timestamp',)  # Filter messages by submission time

    def short_message(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    
    short_message.short_description = 'Message'  # Set column header in the admin interface
