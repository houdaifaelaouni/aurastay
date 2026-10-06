# Builds the React app and serves it on :3000.
# Build context is the repo root (see docker-compose.yml) so checkin-kit is
# copied in and served at /pass.

FROM node:20-alpine AS builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./
COPY checkin-kit/ /app/checkin-kit/

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
RUN yarn build

FROM node:20-alpine
WORKDIR /app
RUN yarn global add serve@14
COPY --from=builder /app/frontend/build ./build
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1
CMD ["serve", "build", "-l", "3000"]
