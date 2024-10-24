FROM python:3.11-slim

RUN apt-get update && apt-get upgrade -y && apt-get install -y supervisor vim procps net-tools iputils-ping
RUN pip install --upgrade pip

WORKDIR /app
COPY . /app
COPY .env /app/.env
COPY .bashrc /root/.bashrc
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5555

CMD ["/usr/bin/supervisord"]
