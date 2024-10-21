# views.py
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView,FormView

from .tasks import run_playwright_action
from .models import Action, Sensor, TestResult, UserProfile
from .serializers import ActionSerializer, SensorSerializer, TestResultSerializer
from .forms import UserForm, UserProfileForm
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import logging
import os
import re
import fnmatch

logger        = logging.getLogger('django')
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

class ConfigView(LoginRequiredMixin, TemplateView):
    # Displays the main board page for logged-in users
    template_name = 'config.html'
    
    def get_context_data(self, **kwargs):
        context                 = super().get_context_data(**kwargs)
        profile, created        = UserProfile.objects.get_or_create(user=self.request.user)
        if(created):
            profile.is_paying_user = False
            profile.save()
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

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get(self, request, *args, **kwargs):
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)
        return self.render_to_response(self.get_context_data(user_form=user_form, profile_form=profile_form))

    def post(self, request, *args, **kwargs):
        user_profile = get_object_or_404(UserProfile, user=request.user)
        user_form = UserForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            return redirect('web_board')

        profile_form = UserProfileForm(instance=user_profile)
        return self.render_to_response(self.get_context_data(user_form=user_form, profile_form=profile_form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_profile'] = UserProfile.objects.get(user=self.request.user)
        context.update(kwargs)
        return context

# API CRUD for Sensor
# -------------------
class ActionRunNowAPI(APIView):
    # Handles running an action immediately for authenticated users
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_id          = "test_action",
        operation_summary     = "Test an Action",
        operation_description = "Execute the specified action identified by 'id' and return the outcome.",
        responses={
            200: openapi.Response(
                description="Action executed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description='Result of the action, e.g., success or fail'),
                        'output': openapi.Schema(type=openapi.TYPE_STRING, description='The output of the executed action')
                    }
                )
            )
        }
    )
    def post(self, request, id):
        try:
            action          = get_object_or_404(Action, pk=id)
            response        = run_playwright_action(id)
            response['url'] = action.sensor.url + action.action_path
            # Check if the current user is allowed to access this action
            if action.sensor.user != request.user:
                logger.error("You do not have permission to access this action's screenshots.")
                raise PermissionDenied("You do not have permission to access this action's screenshots.")
            else:
                return Response(response, status=status.HTTP_200_OK)
        except Action.DoesNotExist as exc:
            logger.error(f"ActionRunNowAPI DoesNotExist {exc}")
            return Response({'error': 'Action not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error(f"ActionRunNowAPI Exception {exc}")
            return Response({'error': 'An unexpected error occurred', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
class ActionScreenshotAPIView(APIView):
    # Handles retrieving the latest screenshot of a specific action for authenticated users
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_id="get_action_screenshot",
        operation_summary="Get the latest Screenshot",
        operation_description="Retrieve the latest screenshot associated with a specific action identified by the 'id' parameter.",
        responses={
            200: openapi.Response(
                description="Screenshot fetched successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="The screenshot image file"
                )
            )
        }
    )
    def get(self, request, id):
        action = get_object_or_404(Action, pk=id)

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
            logger.error(f"Error retrieving screenshot for action {id}: {str(e)}")
            return Response({"error": "An error occurred while retrieving the screenshot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Alpine.js
# -----------------   
class SensorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class   = SensorSerializer
    
    @swagger_auto_schema(
        operation_id="list_sensors",
        operation_summary="List All Sensors",
        operation_description="Retrieve a list of all sensors currently configured in the system.",
        responses={
            200: openapi.Response(
                description="A list of sensors",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='The ID of the sensor'),
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='The name of the sensor'),
                            'url': openapi.Schema(type=openapi.TYPE_STRING, description='URL that the sensor is monitoring'),
                            'frequency': openapi.Schema(type=openapi.TYPE_INTEGER, description='Frequency of monitoring in seconds')
                        }
                    )
                )
            )
        }
    )
    def get_queryset(self):
        return Sensor.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user_profile = self.request.user.userprofile
        sensor_count = Sensor.objects.filter(user=self.request.user).count()
        
        if not user_profile.is_paying_user and sensor_count >= MAX_SENSORS:
            raise serializers.ValidationError({'error': f'Free version can only create up to {MAX_SENSORS} sensors.'})        

        frequency = int(self.request.data.get('frequency', MIN_FREQUENCY))
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            frequency = MIN_FREQUENCY  # Set to minimum frequency if user is not a paying user

        serializer.save(user=self.request.user, frequency=frequency)

    def perform_update(self, serializer):
        user_profile = self.request.user.userprofile
        frequency = int(self.request.data.get('frequency', serializer.instance.frequency))
        
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            frequency = MIN_FREQUENCY  # Set to minimum frequency if user is not a paying user

        serializer.save(frequency=frequency)

class ActionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class   = ActionSerializer

    def get_queryset(self):
        sensor_id = self.request.query_params.get('sensor', None)
        if sensor_id:
            sensor = get_object_or_404(Sensor, id=sensor_id, user=self.request.user)
            return Action.objects.filter(sensor=sensor)
        return Action.objects.filter(sensor__user=self.request.user)

    def perform_create(self, serializer):
        user_profile = self.request.user.userprofile
        sensor = serializer.validated_data['sensor']

        if sensor.user != self.request.user:
            raise PermissionDenied("You do not have permission to add actions to this sensor.")

        action_count = Action.objects.filter(sensor=sensor).count()
        if not user_profile.is_paying_user and action_count >= MAX_ACTIONS:
            raise serializers.ValidationError({'error': f'Free version can only create up to {MAX_ACTIONS} actions per sensor.'})

        serializer.save()

class TestResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class   = TestResultSerializer

    def get_queryset(self):
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        action_id = self.request.query_params.get('action')
        
        if action_id:
            action = get_object_or_404(Action, id=action_id, sensor__user=self.request.user)
            return TestResult.objects.filter(action=action, timestamp__gte=one_hour_ago)

        return TestResult.objects.filter(action__sensor__user=self.request.user, timestamp__gte=one_hour_ago)