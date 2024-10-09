#!/usr/bin/env python

import os
import subprocess
import signal
import sys
import time
import threading
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
ENVIRONMENT  = os.getenv('ENVIRONMENT', 'development').lower()
SERVICE_ROLE = os.getenv('SERVICE_ROLE', 'django').lower()
HOST         = '0.0.0.0'
PORT         = '8010'

# Commands
MANAGE_PY_CMD = ['python', 'manage.py']
NGINX_CMD     = ['nginx']
LOGROTATE_CMD = ['/usr/sbin/logrotate', '/etc/logrotate.d/gunicorn']

# Processes dictionary to keep track of subprocesses
processes = {}

def run_command(command, check=True):
    """Run a command and optionally check for errors."""
    print(f"Running command: {' '.join(command)}")
    result = subprocess.run(command)
    if check and result.returncode != 0:
        sys.exit(result.returncode)

def start_process(name, command):
    """Start a process and track it."""
    print(f"Starting {name}: {' '.join(command)}")
    process = subprocess.Popen(command, preexec_fn=os.setsid)
    processes[name] = process

def stop_process(name):
    """Stop a tracked process."""
    process = processes.get(name)
    if process:
        print(f"Stopping {name}")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10)
            processes.pop(name, None)
            print(f"{name} stopped successfully.")
        except subprocess.TimeoutExpired:
            print(f"{name} did not stop in time; killing it.")
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            processes.pop(name, None)
        except Exception as e:
            print(f"Error stopping {name}: {e}")
            processes.pop(name, None)

def stop_all_processes():
    """Stop all running processes."""
    for name in list(processes.keys()):
        stop_process(name)

def restart_process(name, command):
    """Restart a process."""
    stop_process(name)
    start_process(name, command)

def get_gunicorn_command(reload=False):
    """Construct the Gunicorn command."""
    cmd = [
        'gunicorn',
        '--workers', '2',
        '--bind', f'{HOST}:{PORT}',
        'backend.wsgi:application',
        '--error-logfile', '/app/logs/gunicorn_error.log',
        '--access-logfile', '/app/logs/gunicorn_access.log',
        '--log-level', 'debug',
    ]
    if reload:
        cmd.append('--reload')
    return cmd

def get_celery_worker_command():
    """Construct the Celery worker command."""
    return ['celery','-A', 'backend','worker','--concurrency=2','--loglevel=info',]

def get_celery_beat_command():
    """Construct the Celery beat command."""
    return ['celery','-A', 'backend','beat','--loglevel=info',]

class ChangeHandler(PatternMatchingEventHandler):
    """Watchdog event handler to restart Gunicorn on file changes."""
    def __init__(self):
        super().__init__(patterns=["*.py", "*.html", "*.css", "*.js"])
        self.debounce_timer = None
        self.debounce_delay = 1  # seconds

    def on_any_event(self, event):
        if event.is_directory:
            return
        if self.debounce_timer:
            self.debounce_timer.cancel()
        self.debounce_timer = threading.Timer(self.debounce_delay, self.restart_gunicorn)
        self.debounce_timer.start()

    def restart_gunicorn(self):
        print("File change detected. Restarting Gunicorn...")
        restart_process('gunicorn', get_gunicorn_command(reload=True))

def main():
    # Change directory to /app
    os.chdir('/app')

    # Handle termination signals
    def signal_handler(sig, frame):
        """Handle termination signals and stop all processes."""
        print("Shutting down...")
        stop_all_processes()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Environment: {ENVIRONMENT}")
    print(f"Service Role: {SERVICE_ROLE}")

    if SERVICE_ROLE == 'django':
        # Start Nginx
        run_command(NGINX_CMD)
        # Rotate logs
        run_command(LOGROTATE_CMD)
        # Run database migrations
        run_command(MANAGE_PY_CMD + ['migrate'])
        # Compile translation messages
        run_command(MANAGE_PY_CMD + ['compilemessages'])
        # Collect static files in production
        if ENVIRONMENT in ['prod', 'qa']:
            run_command(MANAGE_PY_CMD + ['collectstatic', '--noinput'])
        # Start Gunicorn
        if ENVIRONMENT == 'development':
            # In development, use watchdog to monitor file changes
            start_process('gunicorn', get_gunicorn_command(reload=True))
            # Set up watchdog
            event_handler = ChangeHandler()
            observer = Observer()
            observer.schedule(event_handler, path='/app', recursive=True)
            observer.start()
            print("Watching for file changes...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()
        else:
            # In production or QA, start Gunicorn without reload
            start_process('gunicorn', get_gunicorn_command())
            # Wait for Gunicorn process to exit
            processes['gunicorn'].wait()

    elif SERVICE_ROLE == 'celery':
        # Start Celery worker
        start_process('celery_worker', get_celery_worker_command())
        # Start Celery beat
        start_process('celery_beat', get_celery_beat_command())
        # Wait for processes to exit
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            stop_all_processes()
    else:
        print(f"Unknown SERVICE_ROLE '{SERVICE_ROLE}'. Exiting.")
        sys.exit(1)

if __name__ == '__main__':
    main()
