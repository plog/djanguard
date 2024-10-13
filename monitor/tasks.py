from .models import Action, TestResult, Sensor
from .serializers import TestResultSerializer
from .selenium_dsl import DSLExecutor
from asgiref.sync import sync_to_async
from celery import shared_task
from celery.schedules import timedelta
from django_celery_results.models import TaskResult
from django.utils import timezone
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
import logging
import aiohttp
import json
import re

logger = logging.getLogger('celery_process')

async def get_favicon(url):
    try:
        # Ensure the URL is formatted as [protocol]://[domain]
        parsed_url = url.split("/")
        base_url = f"{parsed_url[0]}//{parsed_url[2]}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch page, status code: {response.status}")
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                icon_link = None
                
                # Search for favicon link elements
                for link in soup.find_all('link'):
                    rel = link.get('rel', [])
                    if 'icon' in rel or 'shortcut icon' in rel:
                        icon_link = link.get('href')
                        break
                
                # Fallback to /favicon.ico if no link was found
                if not icon_link:
                    icon_link = "/favicon.ico"
                
                # Construct the full URL if needed
                if icon_link and not icon_link.startswith("http"):
                    icon_link = base_url.rstrip('/') + icon_link if icon_link.startswith("/") else f"{base_url.rstrip('/')}/{icon_link}"
                
                # Verify if the favicon link is accessible
                async with session.get(icon_link) as icon_response:
                    if icon_response.status == 200:
                        logger.info(f"Favicon URL: {icon_link}")
                        return icon_link
                    else:
                        logger.error(f"Favicon not found at: {icon_link}")
                        return None
    except Exception as e:
        logger.error(f"Error while fetching favicon: {str(e)}")
        return None

@shared_task()
def delete_old_task_results():
    delta = timezone.now() - timedelta(minutes=15)
    TaskResult.objects.filter(date_done__lt=delta).delete()

@shared_task(bind=True)
def schedule_sensor_actions(self):
    now = timezone.now()
    sensors = Sensor.objects.all()
    processed = []
    for sensor in sensors:
        threshold = now - timedelta(seconds=sensor.frequency)
        actions   = Action.objects.filter(sensor=sensor, last_execution__lt=threshold)
        logger.info(f'PROCESSING SENSOR >{sensor.name}< - {threshold} seconds')
        for action in actions:
            # Schedule the task to run Playwright for this action
            logger.info(f'GO RUN -->> {action.action_name} <<--')
            processed.append(action.id)
            run_playwright_action.delay(action.id)
            action.last_execution = timezone.now()
            action.save()
    return processed

@shared_task(bind=True)
def run_playwright_action(self, action_id):
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_run_playwright_action(action_id))
    return result

async def async_run_playwright_action(action_id):
    # Fetch the action from the database using sync_to_async to avoid async context issue
    action      = await sync_to_async(Action.objects.select_related('sensor').get)(id=action_id)
    sensor      = action.sensor
    test_result = None

    favico = await get_favicon(sensor.url+action.action_path)
    if favico:
        sensor.favico = favico
        await sync_to_async(sensor.save)() 


    # If the action is a simple status code check, use aiohttp for efficiency
    if action.assertion_type == 'status_code':
        async with aiohttp.ClientSession() as session:
            headers = json.loads(action.payload).get('headers', {}) if action.payload else {}
            data    = json.loads(action.payload).get('data', {}) if action.payload else {}
            async with session.request(method=action.action_type, url=action.sensor.url + action.action_path, headers=headers, json=data) as response:
                actual_value = str(response.status)
                logger.info(f'      {action.action_name} status_code:{actual_value}')
                test_result = TestResult(
                    action=action,
                    test_type='status_code',
                    expected_value=action.expected_value,
                    actual_value=actual_value,
                    timestamp=timezone.now(),
                )
                await sync_to_async(test_result.save)()

    # Selenium Style script
    elif action.assertion_type == 'selenium':
        executor    = DSLExecutor(action)
        test_result = await executor.execute()

   # Assertion: Element Exists
    elif action.assertion_type == 'element_exists':
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            sensor_url  = action.sensor.url
            action_path = action.action_path
            start_url   = f"{sensor_url}{action_path}"
            logger.info(f'Opening start URL: {start_url}')
            await page.goto(start_url, timeout=10000)
            logger.info(get_favicon(page))

            if action.selector:
                test_result = TestResult(
                    action        = action,
                    test_type     = action.assertion_type,
                    expected_value= action.expected_value,
                    timestamp     = timezone.now()
                )                
                try:
                    await page.wait_for_selector(action.selector, timeout=5000)
                    actual_value = 'Element Found'
                    test_result.actual_value = actual_value
                except Exception:
                    actual_value             = 'Element Not Found'
                    page_content             = await page.content()
                    soup                     = BeautifulSoup(page_content, 'html.parser')
                    clean_text               = re.sub(r'\s+', ' ', soup.get_text()[:300]).strip()
                    test_result.body         = clean_text
                    test_result.actual_value = actual_value
                    logger.error(f'{action.action_name} keyword:{actual_value}')

            # Close the browser
            await browser.close()
            
    if test_result:
        await sync_to_async(test_result.save)()
    else:
        return {"message": f"Not test result created from Action {action.action_name}"}

    # Serialize the TestResult to return a dictionary representation
    if test_result:
        serializer = TestResultSerializer(test_result)
        logger.info(f"All Good ....... {serializer.data}")
        return serializer.data
    else:
        return {"message": "No test result created."}
