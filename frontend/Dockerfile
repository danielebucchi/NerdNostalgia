FROM node:26-alpine

WORKDIR /app

# Installa dipendenze separatamente per sfruttare la cache layer
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3737

# Dev mode con hot reload (i sorgenti arrivano via bind mount in compose)
CMD ["npm", "run", "dev"]
