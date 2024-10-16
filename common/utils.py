from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from logging.handlers import RotatingFileHandler

import gzip
import logging
import os
import os

logger = logging.getLogger('django')
DATA_DIR       = settings.DATA_DIR


# -------------------------
#       Expose files
# -------------------------
def secure_screenshots_view(request, filename):
    media_dir = os.path.join(DATA_DIR, filename) 

    # Check if the user is authenticated
    if not request.user.is_authenticated:
        logger.error("You are not allowed to access this file")
        return HttpResponseForbidden("You are not allowed to access this file.")

    # Check if the file exists
    if not os.path.exists(media_dir):
        logger.error(f"{media_dir} does not exist")
        return HttpResponseForbidden("File does not exist.")

    # Generate the redirect URL with the token
    response = HttpResponse()
    if not request.headers.get('X-Real-Ip'):
        response.status_code = 404
        response.content = 'The request should be come from Nginx server.'
        return response
    
    redirect_url = f'/mediahttp/{filename}'
    response['X-Accel-Redirect'] = redirect_url
    
    # Set appropriate Content-Type based on file extension
    if filename.endswith('.jpeg') or filename.endswith('.jpg'):
        content_type = 'image/jpeg'
    elif filename.endswith('.mp3'):
        content_type = 'audio/mpeg'
    else:
        content_type = 'application/octet-stream'  # Default for unknown binary files

    response = HttpResponse(open(media_dir, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['Content-Length'] = os.path.getsize(media_dir)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['Accept-Ranges'] = 'bytes'

    # Add X-Accel-Redirect header
    return response

