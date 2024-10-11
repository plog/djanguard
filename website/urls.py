from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('contact/', views.ContactFormView.as_view(), name='contact'),
    path('contact/success/', TemplateView.as_view(template_name="contact/contact_success.html"), name='contact_success'),
    path(''             , views.HomePageView.as_view(), name='home'),
    path('privacy'      , views.PrivacyView.as_view(), name='privacy'),
]
