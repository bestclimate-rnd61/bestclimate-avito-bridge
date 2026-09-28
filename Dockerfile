FROM php:8.2-apache
RUN apt-get update \
 && apt-get install -y --no-install-recommends libcurl4-openssl-dev \
 && docker-php-ext-install curl \
 && rm -rf /var/lib/apt/lists/*
COPY index.html /var/www/html/index.html
COPY send.php /var/www/html/send.php
COPY privacy.html /var/www/html/privacy.html
COPY consent.html /var/www/html/consent.html
EXPOSE 80
