# One image for the API (default), the worker (npm run worker) and migrations (npm run migrate).
# The first stage compiles TypeScript; the second only has production packages and the built JS.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:22-slim
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
COPY migrations ./migrations
# Run as the unprivileged user that ships with the node image, not root.
USER node
# Must match PORT in src/api.ts and the api port in infra/terraform/ecs.tf.
EXPOSE 4000
CMD ["npm", "run", "api"]
