import logging
from urllib.parse import urlparse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

# Define the logger for country restrictions
logger = logging.getLogger('country_restriction')

class DynamicCORSMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        origin = request.META.get('HTTP_ORIGIN')
        if not origin:
            origin = request.META.get('HTTP_REFERER')
            # Parse the origin to get only the scheme, domain, and port (ignore path)
            parsed_origin = urlparse(origin)
            origin = f"{parsed_origin.scheme}://{parsed_origin.netloc}"            

        # Check if the origin is in settings.CORS_ALLOWED_ORIGINS
        if origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
            response['Access-Control-Allow-Origin']  = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
            response['Access-Control-Allow-Headers'] = 'Authorization, X-CSRFToken, Content-Type'
            response['Access-Control-Allow-Credentials'] = 'true'

        elif origin and origin.startswith('chrome-extension://'):
            # Allow chrome extensions
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
            response['Access-Control-Allow-Headers'] = 'Authorization, X-CSRFToken, Content-Type'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        else:
            # Log for non-chrome-extension origins or not allowed origins
            logger.info(f"Rejected origin or disallowed origin: {origin}")
        
        return response
