import logging
from celery import shared_task
from playwright.async_api import async_playwright
from .models import Action, TestResult, Sensor
from django.utils import timezone
from django_celery_results.models import TaskResult
from celery.schedules import timedelta
import asyncio
from asgiref.sync import sync_to_async

logger = logging.getLogger('celery_process')

@shared_task(bind=True)
def schedule_sensor_actions(self):
    now = timezone.now()
    sensors = Sensor.objects.all()
    for sensor in sensors:
        threshold = now - timedelta(seconds=sensor.frequency)
        actions   = Action.objects.filter(sensor=sensor, last_execution__lt=threshold)
        logger.info(f'PROCESSING SENSOR{sensor.name} - {threshold}')
        for action in actions:
            # Schedule the task to run Playwright for this action
            logger.info(f'GO RUN {action.action_name}')
            run_playwright_action.delay(action.id)
            action.last_execution = timezone.now()
            action.save()

            
@shared_task(bind=True)
def run_playwright_action(self, action_id):
    asyncio.run(async_run_playwright_action(action_id))

async def async_run_playwright_action(action_id):
    # Fetch the action from the database using sync_to_async to avoid async context issue
    action = await sync_to_async(Action.objects.select_related('sensor').get)(id=action_id)

    # Start Playwright (async version)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Construct the URL
        url = action.sensor.url + action.action_path
        
        # Perform the action based on action_type
        if action.action_type == 'GET':
            response = await page.goto(url)
        elif action.action_type in ['POST', 'PUT', 'DELETE']: 
            # Convert request body to dictionary if it's not None
            request_body = action.request_body if action.request_body else {}
            response = await page.request.fetch(
                url,
                method=action.action_type,
                data=request_body,
            )
        else:
            raise ValueError("Unsupported action type")

        # Prepare test results
        test_results = []

        # Assertion: Status Code
        if action.assertion_type == 'status_code':
            actual_value = str(response.status) if response else 'No Response'
            test_results.append(
                TestResult(
                    action=action,
                    test_type='status_code',
                    expected_value=action.expected_value,
                    actual_value=actual_value,
                    timestamp=timezone.now(),
                )
            )

        # Assertion: Keyword in Body
        elif action.assertion_type == 'keyword':
            body = await response.text() if response else ''
            actual_value = 'Found' if action.expected_value in body else 'Not Found'
            test_results.append(
                TestResult(
                    action=action,
                    test_type='keyword',
                    expected_value=action.expected_value,
                    actual_value=actual_value,
                    timestamp=timezone.now(),
                )
            )

        # Assertion: Element Exists
        elif action.assertion_type == 'element_exists':
            if action.selector:
                try:
                    await page.wait_for_selector(action.selector, timeout=5000)
                    actual_value = 'Element Found'
                except Exception:
                    actual_value = 'Element Not Found'
                test_results.append(
                    TestResult(
                        action=action,
                        test_type='element_exists',
                        expected_value=action.expected_value,
                        actual_value=actual_value,
                        timestamp=timezone.now(),
                    )
                )

        # Save test results to the database using sync_to_async
        await sync_to_async(TestResult.objects.bulk_create)(test_results)

        # Close the browser
        await browser.close()

        # Return success message for Celery
        return f"Action {action_id} executed successfully with {len(test_results)} test results."
