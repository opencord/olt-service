# docker build -t xos/vnf-proxy .
# docker run --name proxy -p 8000:8000 -d xos/vnf-proxy node proxy.js http://10.128.23.1:8882

FROM node:7.9.0

WORKDIR /var/www

COPY . /var/www

RUN npm install

EXPOSE 8000