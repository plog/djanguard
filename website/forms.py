# forms.py

from django import forms
from django.utils.html import strip_tags
import time
from .models import ContactMessage  # Import the ContactMessage model

class ContactForm(forms.Form):
    name      = forms.CharField(max_length=100, required=True)
    email     = forms.EmailField(required=True)
    message   = forms.CharField(widget=forms.Textarea, required=True)
    timestamp = forms.IntegerField(widget=forms.HiddenInput())  # Hidden field for time validation

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the timestamp field to the current time when the form is initialized
        self.fields['timestamp'].initial = int(time.time())

    def clean_message(self):
        """Clean the message field to ensure no HTML tags are present."""
        message = self.cleaned_data.get('message', '')
        cleaned_message = strip_tags(message)  # Remove any HTML tags
        return cleaned_message

    def clean(self):
        cleaned_data = super().clean()
        timestamp = cleaned_data.get('timestamp')
        current_time = int(time.time())
        
        if current_time - timestamp < 10:  # Minimum time for form submission
            # Raise a non-field error (no field name will be prefixed in the message)
            raise forms.ValidationError("Form submitted too quickly. Please wait a few seconds before submitting.")
        
        return cleaned_data

    def save(self, ip_address=None):
        """Save the form data to the database."""
        data = self.cleaned_data
        # Create a new ContactMessage object and save it to the database
        ContactMessage.objects.create(
            name=data['name'],
            email=data['email'],
            message=data['message'],  # Save the cleaned message without HTML tags
            ip_address=ip_address  # Save the IP address
        )