from django.contrib import admin
from .models import Sensor, Action, TestResult


# Customize Admin site settings
admin.site.site_header = "Djanguard Administration"
admin.site.site_title  = "Djanguard Admin Portal"
admin.site.index_title = "Welcome to Djanguard Monitoring Dashboard"

# Register your models to make them accessible from the Admin
admin.site.register(Sensor)
admin.site.register(Action)
admin.site.register(TestResult)