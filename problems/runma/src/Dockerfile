FROM php:8-apache-buster

EXPOSE 80

COPY app /var/www/html

RUN chown root /var/www/html
RUN chgrp root /var/www/html
RUN chmod -R 555 /var/www/html