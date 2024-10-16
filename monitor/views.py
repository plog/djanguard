# views.py
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from PIL import Image

from .tasks import run_playwright_action
from .models import Action, Sensor, TestResult, UserProfile
from .serializers import ActionSerializer, SensorSerializer, TestResultSerializer

import logging
import os
import re
import fnmatch

logger = logging.getLogger('django')
MIN_FREQUENCY = 30
MAX_SENSORS   = 10
MAX_ACTIONS   = 3

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
        sensor_data = request.POST.copy()
        sensor_data['user'] = request.user.id

        # Check if the user is a paying user
        try:
            user_profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)

        # Limit the number of sensors for non-paying users
        if not user_profile.is_paying_user:
            sensor_count = Sensor.objects.filter(user=request.user).count()
            if sensor_count >= MAX_SENSORS:
                return Response({'error': f'Free version can only create up to {MAX_SENSORS} sensors.'}, status=status.HTTP_400_BAD_REQUEST)
            
        frequency = int(sensor_data.get('frequency', 0))
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            sensor_data['frequency'] = MIN_FREQUENCY  # Force frequency to MIN_FREQUENCY seconds if not a paying user

        # Check if frequency is valid based on user's subscription
        try:
            user_profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)
        frequency = int(sensor_data.get('frequency', 0))
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            return Response({'error': 'Frequency cannot be below MIN_FREQUENCY seconds for non-paying users.'}, status=status.HTTP_400_BAD_REQUEST)

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
        try:
            user_profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)
        
        # Check if the user is a paying user
        user_profile = request.user.userprofile
        frequency    = int(request.data.get('frequency', sensor.frequency))
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            request.data['frequency'] = MIN_FREQUENCY  # Force frequency to MIN_FREQUENCY seconds if not a paying user
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
            user_profile = request.user.userprofile
            if not user_profile.is_paying_user:
                sensor_id = request.data.get('sensor')
                if sensor_id:
                    action_count = Action.objects.filter(sensor_id=sensor_id, sensor__user=request.user).count()
                    if action_count >= MAX_ACTIONS:
                        return Response({'error': f'Free version can only create up to {MAX_ACTIONS} actions per sensor.'}, status=status.HTTP_400_BAD_REQUEST)
                                
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
        
class ActionScreenshotAPIView(APIView):
    # Handles retrieving the latest screenshot of a specific action for authenticated users
    permission_classes = [IsAuthenticated]

    def get(self, request, action_id):
        action = get_object_or_404(Action, pk=action_id)

        # Check if the current user is allowed to access this action
        if action.sensor.user != request.user:
            logger.error("You do not have permission to access this action's screenshots.")
            raise PermissionDenied("You do not have permission to access this action's screenshots.")

        # Construct the path to the screenshot
        screenshot_dir              = os.path.join(settings.DATA_DIR)
        screenshot_filename_pattern = f"{action.id}_{action.sensor.user.id}_*.jpg"
        
        # Find the latest screenshot matching the pattern
        try:
            matching_files = sorted([f for f in os.listdir(screenshot_dir) if fnmatch.fnmatch(f, screenshot_filename_pattern)], key=lambda x: os.path.getmtime(os.path.join(screenshot_dir, x)), reverse=True)
            if not matching_files:
                logger.error(f"No screenshot found in {screenshot_dir} for this pattern {screenshot_filename_pattern}.")
                return Response({"error": "No screenshot found for this action."}, status=status.HTTP_404_NOT_FOUND)

            latest_screenshot = max(matching_files, key=lambda x: os.path.getmtime(os.path.join(screenshot_dir, x)))
            screenshot_path   = os.path.join(screenshot_dir, latest_screenshot)
            
            # Return the screenshot as a binary response
            return FileResponse(open(screenshot_path, 'rb'), content_type='image/png')
        
        except Exception as e:
            logger.error(f"Error retrieving screenshot for action {action_id}: {str(e)}")
            return Response({"error": "An error occurred while retrieving the screenshot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
