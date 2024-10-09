from django import forms
from .models import Sensor, Action

class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = ['name', 'url', 'frequency']

class ActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['sensor', 'action_name', 'request_details', 'response_details']