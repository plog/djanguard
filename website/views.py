from .forms import ContactForm
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy,reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView
from google.auth.transport import requests
from google.oauth2 import id_token

import os
import logging

logger = logging.getLogger('django')

class ContactFormView(FormView):
    template_name = 'contact/contact_form.html'  # Your contact form template
    form_class    = ContactForm
    success_url   = reverse_lazy('contact_success')  # URL to redirect to after successful form submission
    def form_valid(self, form):
        # Save the form data to the database
        ip_address = self.request.META.get('X-REAL-IP')
        form.save(ip_address=ip_address)
        # Continue with the usual form validation process
        return super().form_valid(form)

class HomePageView(TemplateView):
    template_name = 'home.html'

class PrivacyView(TemplateView):
    template_name = 'privacy.html'

class TermsView(TemplateView):
    template_name = 'terms.html'
    
@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthView(View):
    def post(self, request, *args, **kwargs):
        """
        Google calls this URL after the user has signed in with their Google account.
        """
        token = request.POST.get('credential')
        if not token:
            return HttpResponse(status=400)

        try:
            user_data = id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except ValueError:
            return HttpResponse(status=403)

        # Get or create the user in the database.
        email = user_data.get('email')
        if email:
            password = get_random_string(12)  # Generate a random 12-character password
            user, created = User.objects.get_or_create(username=email, defaults={'email': email})
            if created:
                # Set an unusable password since this user logs in via Google
                user.set_unusable_password()
                user.save()
            # Log the user in and set the authentication backend.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Debugging output to check if the user is properly authenticated before redirecting
        print(f"User logged in: {request.user.is_authenticated}, User ID: {request.user.id}")

        return redirect('web_board')