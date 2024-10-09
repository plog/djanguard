from django.db import models
import json

class Sensor(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=200)
    frequency = models.IntegerField(help_text="Frequency in minutes to check the website")

    def __str__(self):
        return self.name

class Action(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    action_name = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    request_details = models.JSONField()
    response_details = models.JSONField()
    test_results = models.JSONField(null=True, blank=True)  # Field to store the test results

    def __str__(self):
        return f"{self.action_name} for {self.sensor.name}"

    def get_request_details(self):
        return json.dumps(self.request_details, indent=4)

    def get_response_details(self):
        return json.dumps(self.response_details, indent=4)

class TestResult(models.Model):
    action    = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='tests')
    test_type = models.CharField(max_length=100, choices=[
        ('status_code', 'Status Code'),
        ('keyword', 'Keyword in Body'),
        ('response_time', 'Response Time'),
    ])
    expected_value = models.CharField(max_length=100, help_text="Expected value for this test")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_type} test for {self.action}"