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
        fields = []  # We are not allowing edits, just displaying data