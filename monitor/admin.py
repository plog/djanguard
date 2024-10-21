from django.contrib import admin
from .models import Sensor, Action, TestResult, UserProfile

# Customize Admin site settings
admin.site.site_header = "Djanguard Administration"
admin.site.site_title = "Djanguard Admin Portal"
admin.site.index_title = "Welcome to Djanguard Monitoring Dashboard"

# Custom Admin for Sensor Model
@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    search_fields = ['name', 'url']
    list_display  = ['id', 'name', 'url', 'favico', 'frequency', 'get_actions_count']

# Custom Admin for Action Model
@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    search_fields = ['action_name', 'action_type', 'sensor__name']
    list_display  = ['id', 'action_name', 'action_type', 'action_path', 'last_execution', 'sensor', 'assertion_type', 'expected_value', 'sequence']

# Custom Admin for TestResult Model
@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    search_fields = ['action__action_name', 'test_type', 'expected_value', 'actual_value']
    list_display  = ['id', 'action', 'test_type', 'expected_value', 'actual_value', 'timestamp']

# Custom Admin for UserProfile Model
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ['user']
    list_display = ['id', 'user', 'is_paying_user']

