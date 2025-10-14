FROM nginx:1.25-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY html/ /usr/share/nginx/html/

COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY images/ /usr/share/nginx/html/images/

EXPOSE 8000