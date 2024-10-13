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
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from .tasks import run_playwright_action
from .models import Action, Sensor, TestResult
from .serializers import ActionSerializer, SensorSerializer, TestResultSerializer

import logging

logger = logging.getLogger('django')

# Pages
#---------------------
class Board(LoginRequiredMixin,TemplateView):
    template_name = 'board.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class SensorList(LoginRequiredMixin,TemplateView):
    template_name = 'sensor_list.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class SensorDetail(LoginRequiredMixin,TemplateView):
    template_name = 'sensor_edit.html'
    # Optionally, you can override the get_context_data method if needed
    # to add extra context to the template.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sensor_id = self.kwargs.get('pk')
        sensor = Sensor.objects.get(pk=sensor_id)
        context['sensor'] = sensor
        return context

class SensorAdd(LoginRequiredMixin,TemplateView):
    template_name = 'sensor_add.html'
    # Optionally, you can override the get_context_data method if needed
    # to add extra context to the template.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  

# API CRUD for Sensor
# -------------------
# Sensors
@method_decorator(ensure_csrf_cookie, name='dispatch')
class SensorListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SensorSerializer

    def get_queryset(self):
        search_term = self.request.headers.get('search', None)
        queryset = Sensor.objects.all()
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)
        return queryset

# Sensors: Retrieve, update, or delete a sensor
@method_decorator(ensure_csrf_cookie, name='dispatch')
class SensorDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Sensor, pk=pk)

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
class ActionListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Action.objects.all()
    serializer_class = ActionSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Handle any other exceptions that may occur
            return Response({
                'error': 'An unexpected error occurred', 
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# Actions Retrieve, update, or delete an action
@method_decorator(ensure_csrf_cookie, name='dispatch')
class ActionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Action, pk=pk)

    def get(self, request, pk):
        action     = self.get_object(pk)
        serializer = ActionSerializer(action)
        return Response(serializer.data)

    def put(self, request, pk):
        action     = self.get_object(pk)
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
class TestResultListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        action_id = request.query_params.get('action_id')
        if action_id:
            test_results = TestResult.objects.filter(action_id=action_id,timestamp__gte=one_hour_ago)
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

class TestResultDetailAPIView(APIView):
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

class ActionRunNowAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, action_id):
        try:
            # Run the asynchronous Playwright function synchronously for immediate execution
            response = run_playwright_action(action_id)
            return Response({'message': f'Action {action_id} executed successfully','response':response}, status=status.HTTP_200_OK)
        except Action.DoesNotExist as exc:
            logger.error(f"ActionRunNowAPIView DoesNotExist {exc}")
            return Response({'error': 'Action not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error(f"ActionRunNowAPIView Exception {exc}")
            return Response({'error': 'An unexpected error occurred', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
