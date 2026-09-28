FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
COPY privacy.html /usr/share/nginx/html/privacy.html
COPY consent.html /usr/share/nginx/html/consent.html
EXPOSE 80
