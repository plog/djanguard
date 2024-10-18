from .models import Action, TestResult, Sensor
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone
from playwright.async_api import async_playwright
from asgiref.sync import sync_to_async
from PIL import Image

import asyncio
import base64
import hashlib
import logging
import re
import traceback
import os
logger = logging.getLogger('celery_process')

class CommandHandler:
    def __init__(self, page):
        self.page = page
        self.secret_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:16] 
    
    async def check_element_exists(self, selector):
        logger.info(f'Checking if element exists: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        assert await self.page.locator(selector).count() > 0, f"Element {selector} not found"

    async def fill_input(self, selector, value):
        logger.info(f'Filling element {selector} with value: {value}')
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.fill(selector, value)

    async def click_element(self, selector):
        logger.info(f'Clicking element: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.click(selector)
        # Wait for navigation and get the new page content
        await self.page.wait_for_load_state('networkidle')
        page_content = await self.page.content()
        return page_content

    async def check_text_present(self, text):
        logger.info(f'Checking if text is present: {text}')
        await self.page.wait_for_timeout(2000)  # Adding a small delay to allow text to appear
        assert await self.page.locator(f'text={text}').count() > 0, f"Text '{text}' not found on page"

    async def assert_title(self, expected_title):
        logger.info(f'Asserting title is: {expected_title}')
        await self.page.wait_for_timeout(2000)
        assert await self.page.title() == expected_title, f"Title does not match: {expected_title}"

    async def assert_element_present(self, selector):
        logger.info(f'Asserting element is present: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        assert await self.page.locator(selector).count() > 0, f"Element {selector} not found"

    async def assert_element_not_present(self, selector):
        logger.info(f'Asserting element is not present: {selector}')
        await self.page.wait_for_timeout(2000)
        assert await self.page.locator(selector).count() == 0, f"Element {selector} is present"

    async def pause_execution(self):
        logger.info('Pausing execution')
        await self.page.pause()

    async def click_at_coordinates(self, x, y):
        logger.info(f'Clicking at coordinates: ({x}, {y})')
        await self.page.mouse.click(int(x), int(y))
        # Wait for navigation and get the new page content
        await self.page.wait_for_load_state('networkidle')
        page_content = await self.page.content()
        return page_content

    async def double_click_element(self, selector):
        logger.info(f'Double-clicking element: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.dblclick(selector)
        # Wait for navigation and get the new page content
        await self.page.wait_for_load_state('networkidle')
        page_content = await self.page.content()
        return page_content

    async def drag_and_drop(self, source, target):
        logger.info(f'Dragging element {source} to {target}')
        await self.page.wait_for_selector(source, timeout=10000)
        await self.page.wait_for_selector(target, timeout=10000)
        await self.page.drag_and_drop(source, target)

    async def mouse_over_element(self, selector):
        logger.info(f'Mouse over element: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.hover(selector)

    async def set_window_size(self, width, height):
        logger.info(f'Setting window size to: {width}x{height}')
        await self.page.set_viewport_size({"width": int(width), "height": int(height)})

    async def handle_if_statement(self, condition):
        match = re.match(r'element present "(.+?)"', condition)
        if match:
            selector = match.group(1)
            logger.info(f'Checking condition if element is present: {selector}')
            return await self.page.locator(selector).count() > 0
        return False

    async def handle_repeat_statement(self, condition, repeat_count):
        match = re.match(r'element not present "(.+?)"', condition)
        if match:
            selector = match.group(1)
            for i in range(int(repeat_count)):
                logger.info(f'Checking repeat condition if element is not present: {selector}, attempt {i + 1}')
                if await self.page.locator(selector).count() == 0:
                    return True
                await self.page.wait_for_timeout(2000)
        return False

    async def get_element_content(self, selector):
        print(f'Getting content of element: {selector}')
        await self.page.wait_for_selector(selector, timeout=10000)
        element_content = await self.page.locator(selector).inner_html()
        print(f'Content of element {selector}: {element_content[:200]}...')  # Log a portion of the content for debugging
        return element_content
        

class DSLExecutor:
    def __init__(self, action):
        self.action           = action
        self.commands         = action.selenium_script
        self.command_registry = [
            (r'check-element-exists "(.+?)"', 'check_element_exists'),
            (r'fill "(.+?)" with "(.+?)"', 'fill_input'),
            (r'click "(.+?)"', 'click_element'),
            (r'check-text "(.+?)" is-present', 'check_text_present'),
            (r'assert title "(.+?)"', 'assert_title'),
            (r'assert element present "(.+?)"', 'assert_element_present'),
            (r'assert element not present "(.+?)"', 'assert_element_not_present'),
            (r'pause', 'pause_execution'),
            (r'click at "(.+?)" "(.+?)"', 'click_at_coordinates'),
            (r'double click "(.+?)"', 'double_click_element'),
            (r'drag and drop "(.+?)" to "(.+?)"', 'drag_and_drop'),
            (r'mouse over "(.+?)"', 'mouse_over_element'),
            (r'set window size "(.+?)" "(.+?)"', 'set_window_size'),
        ]

    async def screenshot(self):
        logger.info(f'Trying to take a Screenshot.....')
        DATA_DIR = settings.DATA_DIR
        testResult = TestResult(
            action         = self.action,
            test_type      = self.action.assertion_type,
            expected_value = 'pass',
            timestamp      = timezone.now(),
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                browser     = await p.chromium.launch()
                page        = await browser.new_page()
                await page.set_viewport_size({"width": 1000, "height": 1000})
                sensor_url  = self.action.sensor.url
                action_path = self.action.action_path      
                          
                await page.goto(sensor_url + action_path)
                user_id         = await sync_to_async(lambda: self.action.sensor.user.id)()
                filename        = f"{self.action.id}_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
                screenshot_path = os.path.join(DATA_DIR, filename)
                                
                await page.screenshot(path=screenshot_path)
                # Resize the image using Pillow
                img = Image.open(screenshot_path)
                img = img.resize((500, 500), Image.LANCZOS)  # Resize to 250x250
                img.save(screenshot_path, quality=50)  # Save with lower quality                
                await browser.close()
                testResult.actual_value = 'pass'
                testResult.body           = filename
                logger.info(f'Screenshot saved at: {screenshot_path}')
            except Exception as exc:
                logger.error(f'Screenshot failed: {exc}')
                logger.error(traceback.format_exc())
                testResult.actual_value = 'fail'
                testResult.body           = exc
            finally:
                await browser.close()
                
        return testResult
                
    async def execute(self):
        # Store the result in TestResult model
        testResult = TestResult(
            action         = self.action,
            test_type      = 'script_execution',
            actual_value   = 'fail',
            expected_value = 'pass',
            timestamp=timezone.now()
        )        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page()
            handler = CommandHandler(page)

            # Automatically open the URL using sensor and action path
            sensor_url  = self.action.sensor.url
            action_path = self.action.action_path
            start_url   = f"{sensor_url}{action_path}"
            logger.info(f'Opening start URL: {start_url}')

            await page.goto(start_url, timeout=10000)

            commands = self.commands.splitlines()
            i = 0
            while i < len(commands):
                command = commands[i].strip()
                handled = False
                try:
                    # Handle if-else conditions
                    if command.startswith('if '):
                        condition = command[3:]
                        if await handler.handle_if_statement(condition):
                            i += 1
                        else:
                            # Skip to the corresponding 'end'
                            while i < len(commands) and not commands[i].startswith('end'):
                                i += 1
                    elif command.startswith('repeat if '):
                        condition, repeat_count = re.match(r'repeat if (.+?) (\d+) times', command).groups()
                        if await handler.handle_repeat_statement(condition, repeat_count):
                            i += 1
                        else:
                            # Skip to the next command if condition is not met
                            i += 1

                    elif command == 'end':
                        # End of an if block
                        i += 1

                    else:
                        # Regular command handling
                        for pattern, method_name in self.command_registry:
                            match = re.match(pattern, command)
                            if match:
                                method = getattr(handler, method_name)
                                await method(*match.groups())
                                handled = True
                                break
                        if not handled:
                            logger.info(f'Unknown command: {command}')
                        i += 1

                except Exception as e:
                    logger.error(f'Error occurred: {str(e)}')
                    page_content     = await page.content()
                    soup             = BeautifulSoup(page_content, 'html.parser')
                    clean_text       = re.sub(r'\s+', ' ', soup.get_text()[:300]).strip()
                    
                    testResult.actual_value = 'fail'
                    testResult.body         = clean_text  # Store part of the page content without HTML tags
                    await browser.close()
                    return testResult
            
            testResult.actual_value = 'pass'
            await browser.close()
            return testResult

