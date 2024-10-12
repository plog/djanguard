from django.db import models
import json

HTTP_VERBS = [
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE'),
            ('PATCH', 'PATCH'),
            ('HEAD', 'HEAD'),
            ('OPTIONS', 'OPTIONS'),
            ('TRACE', 'TRACE')
]

ASSERTION_TYPES = [
    ('status_code', 'Status Code'),
    ('contains_keyword', 'Contains Keyword'),
    ('element_exists', 'Element Exists'),
    ('json_key_exists', 'JSON Key Exists'),
]

class Action(models.Model):
    action_name    = models.CharField(max_length=100)
    action_type    = models.CharField(max_length=10, choices=HTTP_VERBS, default='GET')
    action_path    = models.CharField(default='')
    last_execution = models.DateTimeField(auto_now_add=True)
    request_body   = models.JSONField(null=True, blank=True)
    sensor         = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='actions')
    assertion_type = models.CharField(max_length=50, choices=ASSERTION_TYPES, default='status_code')
    expected_value = models.CharField(max_length=200, help_text="The expected value for this assertion")
    selector       = models.CharField(max_length=200, null=True, blank=True, help_text="CSS Selector (for element_exists type)")  # Only needed for 'element_exists'

    def __str__(self):
        return f"{self.action_name} ({self.get_action_type_display()})"

    def get_request_body(self):
        return json.dumps(self.request_body, indent=4)

    def get_assertion_details(self):
        """
        Returns the details of the assertion for easy reference or logging purposes.
        """
        details = {
            "assertion_type": self.assertion_type,
            "expected_value": self.expected_value,
        }
        if self.assertion_type == "element_exists":
            details["selector"] = self.selector
        return details
    
class Sensor(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=200)
    frequency = models.IntegerField(help_text="Frequency in minutes to check the website")

    def get_actions_count(self, obj):
        return obj.actions.count()  # Count the related actions using the related name 'actions'
    
    def __str__(self):
        return self.name

class TestResult(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='tests')
    test_type = models.CharField(max_length=100, choices=[
        ('status_code', 'Status Code'),
        ('keyword', 'Keyword in Body'),
        ('response_time', 'Response Time'),
    ])
    expected_value = models.CharField(max_length=100, help_text="Expected value for this test")
    actual_value   = models.CharField(max_length=100, null=True, blank=True, help_text="Actual value observed during the test")
    timestamp      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_type} test for action '{self.action.action_name}' at {self.timestamp}"

