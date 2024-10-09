from rest_framework import viewsets
from django.shortcuts import render, redirect
from .models import Sensor, Action, TestResult
from .serializers import SensorSerializer, ActionSerializer, TestResultSerializer
from .forms import SensorForm

class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer

class ActionViewSet(viewsets.ModelViewSet):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer

class TestResultViewSet(viewsets.ModelViewSet):
    queryset = TestResult.objects.all()
    serializer_class = TestResultSerializer

def test_results_view(request):
    actions = Action.objects.all()
    return render(request, 'test_results.html', {'actions': actions})

def add_sensor(request):
    if request.method == 'POST':
        form = SensorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sensor_list')  # Replace with your desired redirect URL
    else:
        form = SensorForm()
    return render(request, 'add_sensor.html', {'form': form})