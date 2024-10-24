from .models import Action, TestResult, Sensor, UserProfile
from .selenium_dsl import DSLExecutor
from .serializers import TestResultSerializer
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from celery import shared_task
from celery.schedules import timedelta
from django_celery_results.models import TaskResult
from django.conf import settings
from django.utils import timezone
from django.db.models import Q


import aiohttp
import asyncio
import json
import logging
import os
import re
import traceback

logger = logging.getLogger('celery_process')

def should_send_notification(current_test_result):
    # Fetch the last test result for the same action before the current one
    previous_test_result = TestResult.objects.filter(
        action=current_test_result.action,
        timestamp__lt=current_test_result.timestamp
    ).order_by('-timestamp').first()
    # Determine the failure state of the current test result
    current_failed = (
        current_test_result.expected_value != current_test_result.actual_value or 
        current_test_result.actual_value == 'fail'
    )
    # If no previous test result exists, this is the first test, so notify if it fails
    if not previous_test_result:
        return current_failed
    
    # Determine the failure state of the previous test result
    previous_failed = (
        previous_test_result.expected_value != previous_test_result.actual_value or 
        previous_test_result.actual_value == 'fail'
    )
    
    # Send notification if:
    # 1. The failure status has changed (current_failed != previous_failed)
    # 2. The actual_value is different from the previous actual_value
    return current_failed != previous_failed or current_test_result.actual_value != previous_test_result.actual_value

# Async function to send a message via Telegram using aiohttp
async def send_telegram_message(bot_token, chat_ids, message):
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with aiohttp.ClientSession() as session:
        for chat_id in chat_ids:
            payload = {'chat_id': chat_id,'text': message}
            async with session.post(telegram_url, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send message to chat_id: {chat_id}. Status: {response.status}")

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
            processed.append(action.id)
            run_playwright_action.delay(action.id)
            action.last_execution = timezone.now()
            action.save()
    return processed

@shared_task(bind=True)
def run_playwright_action(self, action_id):
    loop        = asyncio.get_event_loop()
    test_result = loop.run_until_complete(async_run_playwright_action(action_id))
    logger.info(f"test_result --------- {test_result}")
    
    test_result_db = TestResult.objects.get(id=test_result['id'])
    if should_send_notification(test_result_db):
        # Check if test failed
        if test_result_db.expected_value != test_result_db.actual_value or test_result_db.actual_value == 'fail':
            # Get the user profile related to the action's sensor's user
            user_profile = UserProfile.objects.get(user=test_result_db.action.sensor.user)
            # Prepare the message
            message = f"Test failed for {test_result_db.action.action_name}.\nExpected: {test_result_db.expected_value}\nActual: {test_result_db.actual_value}"
            # Send notification only if there are chat_ids available in the user profile
            if user_profile.telegram_chat_ids:
                loop.run_until_complete(send_telegram_message(settings.BOT_TOKEN, user_profile.telegram_chat_ids, message))

    return test_result

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
    if action.assertion_type in ['status_code','contains_keyword']:
        test_result = TestResult(
            action         = action,
            test_type      = action.assertion_type,
            expected_value = action.expected_value,
            timestamp      = timezone.now(),
            body           = ''
        )        
        try:
            async with aiohttp.ClientSession() as session:
                headers = None
                data    = None
                if action.payload:
                    headers = json.loads(action.payload).get('headers', {}) if action.payload else {}
                    data    = json.loads(action.payload).get('data'   , {}) if action.payload else {}
                async with session.request(method=action.action_type, url=action.sensor.url + action.action_path, headers=headers, json=data) as response:
                    if action.assertion_type =='contains_keyword':
                        response_text = await response.text()
                        if test_result.expected_value in response_text:
                            test_result.actual_value = 'pass'
                            test_result.body = f'{action.action_name} found:{test_result.expected_value}'
                            logger.info(f'{action.action_name} found:{test_result.expected_value}')
                        else:
                            test_result.actual_value = 'fail'
                            test_result.body = f'{action.action_name} Not found:{test_result.expected_value}'
                            logger.error(f'{action.action_name} Not found:{test_result.expected_value}')
                    else:
                        test_result.actual_value = str(response.status)
                        test_result.body = ''
                        logger.info(f'      {action.action_name} status_code:{str(response.status)}')
                        
        except Exception as exc:
            test_result.actual_value = '500'
            test_result.body         = exc
            logger.error(exc)
            logger.error(traceback.format_exc())

    # Selenium Style script
    elif action.assertion_type == 'selenium':
        executor    = DSLExecutor(action)
        test_result = await executor.execute()

    # Playwright screenshot action
    elif action.assertion_type == 'screenshot':
        logger.info(f'Trying to take a Screenshot.....')
        executor    = DSLExecutor(action)
        test_result = await executor.screenshot()
            
    if test_result:
        await sync_to_async(test_result.save)()
    else:
        test_result = TestResult(
            action         = action,
            test_type      = action.assertion_type,
            expected_value = 'fail',
            timestamp      = timezone.now(),
            body           = f"Dunno what to do... :/"
        )          

    # Serialize the TestResult to return a dictionary representation
    serializer = TestResultSerializer(test_result)
    return serializer.data

