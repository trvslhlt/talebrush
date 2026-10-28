# Stage 1: build the React front end.
# webpack 4 fails on Node 17+ (OpenSSL 3 dropped the md4 hash it uses), so pin Node 16.
FROM node:16-bullseye AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY webpack.config.js ./
COPY src ./src
RUN npm run build

# Stage 2: serve the built bundle and the API proxy with Flask.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY config.sql ./
COPY server ./server
COPY --from=build /app/build ./build

ENV FLASK_APP=server/app.py \
    DATABASE_PATH=/data/database.db \
    ML_URL=http://backend:5001/
VOLUME /data
EXPOSE 7082
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=7082"]
