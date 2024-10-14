from django.db import models
from django.contrib.auth.models import User

import json

HTTP_VERBS = [
            ('GET'    , 'GET'),
            ('POST'   , 'POST'),
            ('PUT'    , 'PUT'),
            ('DELETE' , 'DELETE'),
            ('PATCH'  , 'PATCH'),
            ('HEAD'   , 'HEAD'),
            ('OPTIONS', 'OPTIONS'),
            ('TRACE'  , 'TRACE')
]

ASSERTION_TYPES = [
    ('status_code'     , 'Status Code'),
    ('contains_keyword', 'Contains Keyword'),
    ('selenium'        , 'Selenium Style'),
    ('json_key_exists' , 'JSON Key Exists'),
]

class Action(models.Model):
    action_name     = models.CharField(max_length=100)
    action_type     = models.CharField(max_length=10, choices=HTTP_VERBS, default='GET')
    action_path     = models.CharField(default='')
    last_execution  = models.DateTimeField(auto_now_add=True)
    payload         = models.JSONField(null=True, blank=True)
    sensor          = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='actions')
    assertion_type  = models.CharField(max_length=50, choices=ASSERTION_TYPES, default='status_code')
    expected_value  = models.CharField(max_length=200, help_text="The expected value for this assertion")
    selenium_script = models.CharField(null=True, blank=True, help_text="Selenium Style script)") 
    sequence        = models.IntegerField(help_text="Order of the command",default=0) 

    def __str__(self):
        return f"{self.action_name} ({self.get_action_type_display()})"

    def get_payload(self):
        return json.dumps(self.payload, indent=4)

class Sensor(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sensors')
    name      = models.CharField(max_length=100)
    url       = models.URLField(max_length=200)
    favico    = models.CharField(null=True, blank=True)
    frequency = models.IntegerField(help_text="Frequency in minutes to check the website")

    def get_actions_count(self):
        return self.actions.count()
    
    def __str__(self):
        return self.name

class TestResult(models.Model):
    action         = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='tests')
    test_type      = models.CharField(max_length=100, choices=ASSERTION_TYPES)
    expected_value = models.CharField(max_length=100, help_text="Expected value for this test")
    actual_value   = models.CharField(max_length=100, null=True, blank=True, help_text="Actual value observed during the test")
    timestamp      = models.DateTimeField(auto_now_add=True)
    body           = models.CharField(max_length=255, null=True, blank=True, help_text="Add more context to the results")

    def __str__(self):
        return f"{self.test_type} test for action '{self.action.action_name}' at {self.timestamp}"

