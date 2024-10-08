# Stage 1: Build the Vite app
FROM node:22.8.0-alpine AS build-stage

# Set working directory inside the container
WORKDIR /app

# Copy the package.json and yarn.lock to install dependencies
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install

# Copy the rest of the app's source code
COPY . .

# Build the Vite app
RUN yarn build

# Stage 2: Serve the Vite app with NGINX
FROM nginx:alpine AS production-stage

# Copy the built Vite app from the build-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy a custom NGINX configuration if needed
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 to the outside world
EXPOSE 80

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]
