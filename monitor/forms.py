# forms.py
from django import forms
from .models import UserProfile, User

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['telegram_chat_ids']
        widgets = {
            'telegram_chat_ids': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'cols': 10})  # Limit to 5 rows
        }