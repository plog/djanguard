from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from monitor.models import UserKey
import logging

logger = logging.getLogger('django')

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Get the Authorization header from the request
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        # Split the header, making "Bearer" optional
        try:
            parts = auth_header.split()
            if len(parts) == 1:
                key = parts[0]  # If no prefix, consider it the key directly
            elif len(parts) == 2 and parts[0].lower() == "bearer":
                key = parts[1]  # Bearer <token> format
            else:
                raise AuthenticationFailed("Invalid token header")
        except ValueError:
            raise AuthenticationFailed("Invalid token header")

        # Try to retrieve the UserKey from the database
        try:
            user_key = UserKey.objects.get(key=key)
        except UserKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")

        return (user_key.user, None)