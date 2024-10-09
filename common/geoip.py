import logging
from django.http import HttpResponseForbidden
from django.contrib.gis.geoip2 import GeoIP2
from django.conf import settings
from django.core.cache import cache

ALLOWED_COUNTRY_CODE = 'ID'  # Replace 'ID' with your desired country code (e.g., 'ID' for Indonesia)

# Middleware
class CountryRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.geoip = GeoIP2()
        self.logger = logging.getLogger('country_restriction')

    def __call__(self, request):
        ip = request.META.get('HTTP_X_REAL_IP')
        url = request.build_absolute_uri()
        if ip and ip != '127.0.0.1':
            try:
                country = self.geoip.country(ip)
                request.country_code = country['country_code']
                self.logger.info(f"IP: {ip} - Country: {country['country_name']} ({country['country_code']}) - URL: {url}")
                # if country['country_code'] != ALLOWED_COUNTRY_CODE:
                #     return HttpResponseForbidden(f"Access denied: {country}")
            except Exception as e:
                self.logger.error(f"Unknown country: {ip} - URL: {url} - {e}")
                # return HttpResponseForbidden(f"Access denied: {ip}")
                
        response = self.get_response(request)
        return response 
    
class BruteForceProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('country_restriction')

    def __call__(self, request):
        response = self.get_response(request)
        # Check if the request is for the login page and the method is POST
        if (request.path == settings.LOGIN_URL or request.path == '/admin/login/') and request.method == "POST":

            # Get the IP address of the client
            ip_address = request.META.get("REMOTE_ADDR")

            # Increment the failed login attempt count for this IP address
            cache_key = f"login_attempts:{ip_address}"
            login_attempts = cache.get(cache_key, 0)

            self.logger.info(f"{ip_address} {login_attempts} Login {request.path} - {response.status_code}")  # For debugging, print the response object            
            cache.set(cache_key, login_attempts + 1, timeout=settings.BRUTE_FORCE_TIMEOUT)

            # If the login attempts exceed the threshold, block further attempts
            if login_attempts >= settings.BRUTE_FORCE_THRESHOLD:
                msg = f"Too many login attempts...."
                self.logger.error(msg)
                return HttpResponseForbidden(msg)

        return response
    
# Pre-processor
def country_code(request):
    geoip = GeoIP2()
    ip    = request.META.get('HTTP_X_REAL_IP')
    if ip == '127.0.0.1':
        country_code = 'Localhost'
    else:
        country_code = None
        try:
            country = geoip.country(ip)
            country_code = country['country_code']
        except Exception as e:
            country_code = 'Unknown'  # Handle cases where the country code cannot be determined

    return {'country_code': country_code}