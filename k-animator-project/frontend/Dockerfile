FROM nginx:1.25-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY frontend/html/ /usr/share/nginx/html/
COPY frontend/css/ /usr/share/nginx/html/css/
COPY frontend/js/ /usr/share/nginx/html/js/
COPY frontend/images/ /usr/share/nginx/html/images/

EXPOSE 8000