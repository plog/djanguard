# yourapp/context_processors.py
from django.conf import settings

def admin_url(request):
    """
    Make the ADMIN_URL available in all templates.
    """
    return {
        'ADMIN_URL': settings.ADMIN_URL
    }