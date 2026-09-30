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
USER node
EXPOSE 4000
CMD ["npm", "run", "api"]
