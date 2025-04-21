FROM node:18-alpine

WORKDIR /site

COPY . /site

RUN npm install serve


EXPOSE 5173

CMD [ "npx", "serve", "-l", "5173", "."]