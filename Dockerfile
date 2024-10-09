FROM plog/djanguard_base:0.1
WORKDIR /app
COPY ./config/gunicorn-logrotate.conf /etc/logrotate.d/gunicorn
RUN chmod 0644 /etc/logrotate.d/gunicorn
# No CMD, this will be set in docker-compose.yml