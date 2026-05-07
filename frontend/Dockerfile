# Build stage
FROM node:20-alpine AS build
WORKDIR /build

COPY proxy-ca.crt /tmp/proxy-ca.crt
ENV NODE_EXTRA_CA_CERTS=/tmp/proxy-ca.crt

COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage
FROM ai-attendance-system-frontend:latest
WORKDIR /app

# Trust proxy CA so apk can reach Alpine mirrors
COPY proxy-ca.crt /tmp/proxy-ca.crt
RUN cat /tmp/proxy-ca.crt >> /etc/ssl/certs/ca-certificates.crt && \
    apk add --no-cache nginx

COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/http.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
