# Docker
docker build -f Dockerfile.base -t plog/djanguard_base:0.1 .

# Django
```
python manage.py makemigrations djanguard 
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

python manage.py makemessages -l fr ; python manage.py makemessages -l id ; python manage.py makemessages -l en
```

## Testing background processes
python manage.py shell -c "from processing.tasks import process_sessions; process_sessions()"

## Env
```
ENVIRONMENT=development
DEBUG=True
ADMIN_URL=..............
LETSENCRYPT_HOST=.......
LETSENCRYPT_EMAIL=......
SECRET_KEY=.............
GOOGLE_MAP_API=.........
CELERY_BROKER_URL='redis://djanguard_redis:6379/1'
DB_NAME=djanguard
DB_USER=djanguard
DB_PASSWORD=............
DB_HOST=djanguard_postgresql

DB_EXTERNAL_PORT=5534
```