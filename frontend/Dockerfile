FROM node:22-alpine AS build
WORKDIR /app
ENV CI=true
COPY package*.json pnpm-lock.yaml* ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]