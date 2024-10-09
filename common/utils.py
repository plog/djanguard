from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from logging.handlers import RotatingFileHandler


import gzip
import logging
import os
import os

logger = logging.getLogger('django')
BASE_DIR       = settings.BASE_DIR
DATA_DIR       = settings.DATA_DIR
MAP_DIR        = settings.MAP_DIR
ARCHIVE_DIR    = settings.ARCHIVE_DIR
GOOGLE_MAP_API = settings.GOOGLE_MAP_API


# -------------------------
#       Expose files
# -------------------------
def secure_file_view(request, session_id, filename):
    media_dir = os.path.join(DATA_DIR, f'session_{session_id}', filename) 

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
    
    token = settings.MEDIA_ACCESS_TOKEN
    redirect_url = f'/mediahttp/session_{session_id}/{filename}'
    response['X-Accel-Redirect'] = redirect_url
    response['X-Media-Token']    = token
    
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


    logger.info(response.headers,token)

    # Add X-Accel-Redirect header
    return response

class GzipRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        super().doRollover()  # Call the base class method to handle log rotation
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                dfn = f"{self.baseFilename}.{i + 1}"
                if os.path.exists(sfn):
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1"
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, dfn)
                with open(dfn, 'rb') as f_in, gzip.open(dfn + '.gz', 'wb') as f_out:
                    f_out.writelines(f_in)
                os.remove(dfn)  # Remove uncompressed file after gzipping

