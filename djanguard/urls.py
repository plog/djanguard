from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.conf import settings
from rest_framework.documentation import include_docs_urls

urlpatterns = [
    path('accounts/'     , include('django.contrib.auth.urls')),
    path('docs/'         , include_docs_urls(title='My API Docs')),
    path('logout/'       , LogoutView.as_view(), name='logout'),
    
    path(f'{settings.ADMIN_URL}/' , admin.site.urls),
    path('', include('monitor.urls')), 
    path('', include('website.urls')),
]
 