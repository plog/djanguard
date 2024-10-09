from celery import shared_task
from .models import Sensor, Action
from django.utils import timezone
from playwright.sync_api import sync_playwright

@shared_task
def check_website(sensor_id):
    sensor = Sensor.objects.get(id=sensor_id)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            response = page.goto(sensor.url)
            response_data = {
                "status_code": response.status(),
                "headers": dict(response.headers()),
                "body": response.text()
            }
            request_data = {
                "method": "GET",
                "url": sensor.url
            }
        except Exception as e:
            response_data = {"error": str(e)}
            request_data = {"method": "GET", "url": sensor.url}

        action = Action.objects.create(
            sensor=sensor,
            action_name="Website Check",
            request_details=request_data,
            response_details=response_data,
            timestamp=timezone.now()
        )

        browser.close()