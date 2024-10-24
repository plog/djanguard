#!/usr/bin/env python

import logging
import logging.handlers
import os
import psutil
import re
import signal
import subprocess
import sys
import threading
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dotenv import load_dotenv
import graypy

load_dotenv()

ENVIRONMENT         = os.getenv('ENVIRONMENT', 'development').lower()
SERVICE_ROLE        = os.getenv('SERVICE_ROLE', 'django').lower()
MEDIA_ACCESS_TOKEN  = os.getenv('MEDIA_ACCESS_TOKEN')
GRAYLOG_HOST        = os.getenv('GRAYLOG_HOST', 'graylog')  # Graylog server host
GRAYLOG_PORT        = int(os.getenv('GRAYLOG_PORT', 12201))   # Graylog port (default is 12201 for GELF UDP)
MANAGE_PY_CMD       = ['python', 'manage.py']
NGINX_CMD           = ['/usr/sbin/nginx']
NGINX_CONF_TEMPLATE = '/app/config/djanguard_nginx.conf'
NGINX_CONF_PATH     = '/etc/nginx/conf.d/default.conf'
APP_NAME            = os.getenv('APP_NAME')

# Set up the logger
logger = logging.getLogger('superstart')
logger.setLevel(logging.INFO)

# Add Graylog handler
graylog_handler = graypy.GELFUDPHandler(GRAYLOG_HOST, GRAYLOG_PORT)  # Use GELFTCPHandler for TCP
logger.addHandler(graylog_handler)

# Optionally, add console handler for local development
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


BEAT_CMD     = ['celery', '-A', APP_NAME, 'beat'  ,'--loglevel=info','--logfile=/app/logs/celery_beat.log']
CELERY_CMD   = ['celery', '-A', APP_NAME, 'worker','--concurrency=5','--loglevel=info','--logfile=/app/logs/celery_worker.log']
GUNICORN_CMD = ['gunicorn','--workers', '2','--bind', '127.0.0.1:5000',f'{APP_NAME}.wsgi:application','--error-logfile', '/app/logs/gunicorn_error.log','--access-logfile', '/app/logs/gunicorn_access.log','--log-level', 'info']

processes = {}

def run_command(command):
    """Run a shell command and log its output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True) 
        logger.info(f"{result.stdout}")
        if result.stderr:
            logger.warning(f"Error Output: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{' '.join(command)}' failed with error: {e.stderr}")
        sys.exit(1)

def start_process(name, command):
    """Start a process and track it."""
    logger.info(f"Starting {name}: {' '.join(command)}")
    process = subprocess.Popen(command, preexec_fn=os.setsid)
    processes[name] = process
    logger.info(f"PID: {process.pid}")
    return process.pid

def stop_process(name):
    """Stop a tracked process."""
    process = processes.get(name)
    if process:
        logger.info(f"Stopping {name}")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10)
            processes.pop(name, None)
            logger.info(f"{name} stopped successfully.")
        except subprocess.TimeoutExpired:
            logger.info(f"{name} did not stop in time; killing it.")
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            processes.pop(name, None) 
        except Exception as e:
            logger.info(f"Error stopping {name}: {e}")
            processes.pop(name, None)

def restart_process(name, command):
    """Restart a process."""
    stop_process(name)
    start_process(name, command)

def reload_gunicorn():
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if '/usr/local/bin/gunicorn' in proc.info['cmdline']:
                pid = proc.info['pid']
                os.kill(pid, signal.SIGHUP)
                logger.info(f"SIGHUP signal sent to gunicorn process with PID: {pid}")
    except Exception as e:
        logger.error(f"Error sending SIGHUP to gunicorn processes: {e}")

def reload_celery_processes():
    """Find all Celery worker and beat processes and send them SIGUSR1 to gracefully reload."""
    try:
        restart_process('celery_worker', CELERY_CMD)
        restart_process('celery_beat'  , BEAT_CMD)
    except Exception as e:
        logger.error(f"Error sending signal to Celery processes: {e}")

class ChangeHandler(PatternMatchingEventHandler):
    """Watchdog event handler to restart Gunicorn on file changes."""
    def __init__(self):
        super().__init__(
            patterns=["*.py", "*.html", "*.css", "*.js", ".env"],
            ignore_patterns=["*.pyc", "*__pycache__*", "*/logs/*", "*.log", "*.swp", "*.tmp","*/static/*", "*/media/*"],
            ignore_directories=True
        )
        self.debounce_timer = None
        self.debounce_delay = 1  # seconds

    def on_modified(self, event):
        if event.is_directory:
            return
        logger.info(f"Event detected: {event.event_type} on {event.src_path}")        
        if self.debounce_timer:
            self.debounce_timer.cancel()
        self.debounce_timer = threading.Timer(self.debounce_delay, self.restart_services)
        self.debounce_timer.start()

    def restart_services(self):
        logger.info("File change detected: restarting services...")
        if SERVICE_ROLE == 'celery':
            reload_celery_processes()

        if SERVICE_ROLE == 'django':
            # run_command(MANAGE_PY_CMD + ['compilemessages'])
            run_command(MANAGE_PY_CMD + ['collectstatic', '--noinput'])
            reload_gunicorn()

# ----------------------------------------------
# Main process
# ----------------------------------------------
def setup_django_services():
    """Setup services for the Django role."""
    run_command(MANAGE_PY_CMD + ['migrate'])
    # run_command(MANAGE_PY_CMD + ['compilemessages'])
    run_command(MANAGE_PY_CMD + ['collectstatic', '--noinput'])
    run_command(NGINX_CMD)
    start_process('gunicorn', GUNICORN_CMD)

def setup_celery_services():
    """Setup services for the Celery role."""
    start_process('celery_worker', CELERY_CMD)
    start_process('celery_beat'  , BEAT_CMD)

def start_watchdog():
    """Start watchdog to monitor file changes."""
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='/app', recursive=True)
    observer.start()
    logger.info("Watching for file changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def wait_for_process(name):
    """Wait for a specific process to finish."""
    process = processes.get(name)
    if process:
        process.wait()

def main():
    os.chdir('/app')

    logger.info("\n--------------------------------")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Service Role: {SERVICE_ROLE}")
    logger.info("--------------------------------\n")

    # ---------------- Django
    if SERVICE_ROLE == 'django':
        setup_django_services()
        if ENVIRONMENT == 'development':
            start_watchdog()
        else:
            wait_for_process('gunicorn')

    # ---------------- Celery
    elif SERVICE_ROLE == 'celery':
        setup_celery_services()
        if ENVIRONMENT == 'development':
            start_watchdog()
        else:
            wait_for_process('celery')
            while True:
                time.sleep(1)            

    else:
        logger.error(f"Unknown SERVICE_ROLE '{SERVICE_ROLE}'. Exiting.")
        sys.exit(1)

if __name__ == '__main__':
    main()
