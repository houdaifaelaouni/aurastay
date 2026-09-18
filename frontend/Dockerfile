# Frontend Dockerfile for React (CRA)
# Multi-stage build for optimized production image

# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies (without frozen-lockfile to allow resolution updates)
RUN yarn install --production=false --ignore-engines

# Copy source files
COPY . .

# Build the app
RUN yarn build --ignore-engines

# Stage 2: Serve the built app
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/build ./build

# Install serve to run the production build
RUN yarn global add serve

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run the server
CMD ["serve", "-s", "build", "-l", "3000"]
