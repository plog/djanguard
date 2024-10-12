from rest_framework import serializers
from .models import Action, Sensor, TestResult
from django.db.models import Count

class SensorSerializer(serializers.ModelSerializer):
    actions_count = serializers.SerializerMethodField()
    class Meta:
        model = Sensor
        fields = '__all__'

    def get_actions_count(self, obj):
        return obj.actions.count()  # Count the related actions using the related name 'actions'
    
class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = '__all__'

class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestResult
        fields = '__all__'