# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Inject proxy CA cert so npm SSL works
COPY proxy-ca.crt /tmp/proxy-ca.crt
ENV NODE_EXTRA_CA_CERTS=/tmp/proxy-ca.crt

COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
