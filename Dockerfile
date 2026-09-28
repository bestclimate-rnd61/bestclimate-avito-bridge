FROM php:8.3-apache

RUN apt-get update \
 && apt-get install -y --no-install-recommends libcurl4-openssl-dev \
 && docker-php-ext-install curl \
 && rm -rf /var/lib/apt/lists/*

COPY korziny-preview/ /var/www/html/
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
