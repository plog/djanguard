# views.py
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from .tasks import run_playwright_action
from .models import Action, Sensor, TestResult
from .serializers import ActionSerializer, SensorSerializer, TestResultSerializer

import logging

logger = logging.getLogger('django')

# Pages
#---------------------
class BoardView(LoginRequiredMixin, TemplateView):
    # Displays the main board page for logged-in users
    template_name = 'board.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class SensorDetailView(LoginRequiredMixin, TemplateView):
    # Displays the details of a specific sensor for editing by logged-in users
    template_name = 'sensor_edit.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sensor_id = self.kwargs.get('pk')
        sensor = Sensor.objects.get(pk=sensor_id)
        context['sensor'] = sensor
        return context

class SensorAddView(LoginRequiredMixin, TemplateView):
    # Displays the form for adding a new sensor, ensuring it is owned by the connected user
    template_name = 'sensor_add.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        # Ensure the new sensor is owned by the connected user
        sensor_data         = request.POST.copy()
        sensor_data['user'] = request.user.id
        serializer = SensorSerializer(data=sensor_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  

# API CRUD for Sensor
# -------------------
# Sensors
@method_decorator(ensure_csrf_cookie, name='dispatch')
class SensorListCreateAPI(ListCreateAPIView):
    # Handles listing and creating sensors for authenticated users
    permission_classes = [IsAuthenticated]
    serializer_class = SensorSerializer

    def get_queryset(self):
        search_term = self.request.headers.get('search', None)
        queryset = Sensor.objects.filter(user=self.request.user).order_by('id')
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)
        return queryset

@method_decorator(ensure_csrf_cookie, name='dispatch')
class SensorDetailAPI(APIView):
    # Handles retrieving, updating, and deleting a specific sensor for authenticated users
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        sensor = get_object_or_404(Sensor, pk=pk)
        if sensor.user != self.request.user:
                raise PermissionDenied("You do not have permission to access this sensor.")
        return sensor

    def get(self, request, pk):
        sensor = self.get_object(pk)
        serializer = SensorSerializer(sensor)
        return Response(serializer.data)

    def put(self, request, pk):
        sensor = self.get_object(pk)
        serializer = SensorSerializer(sensor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        sensor = self.get_object(pk)
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Actions
@method_decorator(ensure_csrf_cookie, name='dispatch')
class ActionListCreateAPI(ListCreateAPIView):
    # Handles listing and creating actions for authenticated users
    permission_classes = [IsAuthenticated]
    serializer_class = ActionSerializer

    def get_queryset(self):
        sensor_id = self.request.query_params.get('sensor', None)
        queryset = Action.objects.filter(sensor__user=self.request.user).order_by('id')
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'error': 'An unexpected error occurred', 
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(ensure_csrf_cookie, name='dispatch')
class ActionDetailAPI(APIView):
    # Handles retrieving, updating, and deleting a specific action for authenticated users
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Action, pk=pk)

    def get(self, request, pk):
        action = self.get_object(pk)
        serializer = ActionSerializer(action)
        return Response(serializer.data)

    def put(self, request, pk):
        action = self.get_object(pk)
        serializer = ActionSerializer(action, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        action = self.get_object(pk)
        action.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# TestResult
class TestResultListAPI(APIView):
    # Handles listing recent test results and creating new ones for authenticated users
    permission_classes = [IsAuthenticated]

    def get(self, request):
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        action_id = request.query_params.get('action')
        if action_id:
            test_results = TestResult.objects.filter(action_id=action_id, timestamp__gte=one_hour_ago)
        else:
            test_results = TestResult.objects.filter(timestamp__gte=one_hour_ago)
        serializer = TestResultSerializer(test_results, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TestResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestResultDetailAPI(APIView):
    # Handles retrieving, updating, and deleting a specific test result for authenticated users
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return TestResult.objects.get(pk=pk)
        except TestResult.DoesNotExist:
            return None

    def get(self, request, pk):
        test_result = self.get_object(pk)
        if test_result is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TestResultSerializer(test_result)
        return Response(serializer.data)

    def put(self, request, pk):
        test_result = self.get_object(pk)
        if test_result is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TestResultSerializer(test_result, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        test_result = self.get_object(pk)
        if test_result is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        test_result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ActionRunNowAPI(APIView):
    # Handles running an action immediately for authenticated users
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        try:
            action = get_object_or_404(Action, pk=action_id)
            response = run_playwright_action(action_id)
            response['url'] = action.sensor.url + action.action_path
            return Response({
                'message': f'Action {action_id} executed successfully',
                'response': response
            }, status=status.HTTP_200_OK)
        except Action.DoesNotExist as exc:
            logger.error(f"ActionRunNowAPI DoesNotExist {exc}")
            return Response({'error': 'Action not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error(f"ActionRunNowAPI Exception {exc}")
            return Response({'error': 'An unexpected error occurred', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)