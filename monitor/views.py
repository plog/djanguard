# views.py


from .forms import UserForm, UserProfileForm
from .models import Action, Sensor, TestResult, UserProfile, UserKey
from .serializers import ActionSerializer, SensorSerializer, TestResultSerializer
from .tasks import run_playwright_action

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView,FormView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from common.authentication import APIKeyAuthentication
from rest_framework import serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

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
        user_form             = UserForm(instance=request.user)
        profile_form          = UserProfileForm(instance=user_profile)
        user_keys             = UserKey.objects.filter(user=request.user) 
        return self.render_to_response(self.get_context_data(
            user_form=user_form, 
            profile_form=profile_form,
            user_keys=user_keys
            ))

    def post(self, request, *args, **kwargs):
        if 'generate_key' in request.POST:
            return self.generate_key(request)
        elif 'delete_key' in request.POST:
            return self.delete_key(request)
                
        user_profile = get_object_or_404(UserProfile, user=request.user)
        user_form = UserForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            return redirect('web_board')

        profile_form = UserProfileForm(instance=user_profile)
        user_keys = UserKey.objects.filter(user=request.user)
        return self.render_to_response(self.get_context_data(
            user_form=user_form, 
            profile_form=profile_form,
            user_keys=user_keys
            ))

    def generate_key(self, request):
        # Generate a new key for the user
        UserKey.objects.create(user=request.user)
        messages.success(request, "A new key has been successfully generated.")
        return redirect(reverse('profile'))

    def delete_key(self, request):
        # Handle key deletion
        key_id = request.POST.get('delete_key')
        key = get_object_or_404(UserKey, id=key_id, user=request.user)
        key.delete()
        messages.success(request, "The key has been deleted successfully.")
        return redirect(reverse('profile'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_profile'] = UserProfile.objects.get(user=self.request.user)
        context.update(kwargs)
        return context

# CRUD API
# -------------------  
class SensorViewSet(viewsets.ModelViewSet):
    authentication_classes = [APIKeyAuthentication, SessionAuthentication]
    permission_classes     = [IsAuthenticated]
    serializer_class       = SensorSerializer
    throttle_classes       = [UserRateThrottle]
    
    @swagger_auto_schema(tags=['Sensors'])
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Sensor.objects.filter(user=self.request.user)
        else:
            return None

    @swagger_auto_schema(tags=['Sensors'])
    def perform_create(self, serializer):
        user_profile = self.request.user.userprofile
        sensor_count = Sensor.objects.filter(user=self.request.user).count()
        
        if not user_profile.is_paying_user and sensor_count >= MAX_SENSORS:
            raise serializers.ValidationError({'error': f'Free version can only create up to {MAX_SENSORS} sensors.'})        

        frequency = int(self.request.data.get('frequency', MIN_FREQUENCY))
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            frequency = MIN_FREQUENCY  # Set to minimum frequency if user is not a paying user

        serializer.save(user=self.request.user, frequency=frequency)

    @swagger_auto_schema(tags=['Sensors'])
    def perform_update(self, serializer):
        user_profile = self.request.user.userprofile
        frequency   = int(self.request.data.get('frequency', serializer.instance.frequency))
        
        if not user_profile.is_paying_user and frequency < MIN_FREQUENCY:
            frequency = MIN_FREQUENCY  # Set to minimum frequency if user is not a paying user

        serializer.save(frequency=frequency)

    @swagger_auto_schema(tags=['Sensors'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Sensors'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Sensors'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Sensors'])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Sensors'])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Sensors'])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class ActionViewSet(viewsets.ModelViewSet):
    authentication_classes = [APIKeyAuthentication, SessionAuthentication]
    permission_classes     = [IsAuthenticated]
    serializer_class       = ActionSerializer
    throttle_classes       = [UserRateThrottle]    

    @swagger_auto_schema(tags=['Actions'])
    def get_queryset(self):
        if self.request.user.is_authenticated:
            sensor_id = self.request.query_params.get('sensor', None)
            if sensor_id:
                sensor = get_object_or_404(Sensor, id=sensor_id, user=self.request.user)
                return Action.objects.filter(sensor=sensor)
            return Action.objects.filter(sensor__user=self.request.user)
        else:
            return None    

    @swagger_auto_schema(tags=['Actions'])
    def perform_create(self, serializer):
        user_profile = self.request.user.userprofile
        sensor = serializer.validated_data['sensor']
        if sensor.user != self.request.user:
            raise PermissionDenied("You do not have permission to add actions to this sensor.")

        action_count = Action.objects.filter(sensor=sensor).count()
        if not user_profile.is_paying_user and action_count >= MAX_ACTIONS:
            raise serializers.ValidationError({'error': f'Free version can only create up to {MAX_ACTIONS} actions per sensor.'})

        serializer.save()

    @swagger_auto_schema(tags=['Actions'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Actions'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Actions'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Actions'])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Actions'])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Actions'])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    # Custom action: POST /actions/{id}/run/
    @swagger_auto_schema(tags=['Actions'])
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        try:
            action          = get_object_or_404(Action, pk=pk)
            response        = run_playwright_action(pk)
            response['url'] = action.sensor.url + action.action_path
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
       
    # Custom action: GET /actions/{id}/screenshot/
    @swagger_auto_schema(tags=['Actions'])
    @action(detail=True, methods=['get'])
    def screenshot(self, request, pk=None):
        action = get_object_or_404(Action, pk=pk)
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
            logger.error(f"Error retrieving screenshot for action {pk}: {str(e)}")
            return Response({"error": "An error occurred while retrieving the screenshot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestResultViewSet(viewsets.ModelViewSet):
    authentication_classes = [APIKeyAuthentication, SessionAuthentication]
    permission_classes     = [IsAuthenticated]
    serializer_class       = TestResultSerializer
    http_method_names      = ['get']
    throttle_classes       = [UserRateThrottle]

    # Add schema information for Swagger documentation
    @swagger_auto_schema(tags=['Test Results'])
    def list(self, request, *args, **kwargs):
        action_id = request.query_params.get('action')
        if not action_id:
            return Response(
                {"detail": "An 'action' query parameter is required to list test results."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)    
    
    @swagger_auto_schema(tags=['Test Results'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
            action_id = self.request.query_params.get('action')
            
            if action_id:
                action = get_object_or_404(Action, id=action_id, sensor__user=self.request.user)
                return TestResult.objects.filter(action=action, timestamp__gte=one_hour_ago)

            return TestResult.objects.filter(action__sensor__user=self.request.user, timestamp__gte=one_hour_ago)
        else:
            return None
