FROM node:18-alpine

WORKDIR /site

COPY . /site

RUN npm install -g http-server


EXPOSE 5173

CMD ["http-server", "-p", "5173", "."]