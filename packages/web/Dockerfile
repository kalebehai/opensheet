FROM node:22-alpine
WORKDIR /app
# Build context is the repo's packages/ dir so ../shared resolves.
COPY shared ./shared
COPY web/package.json ./web/
WORKDIR /app/web
RUN npm install
COPY web ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
