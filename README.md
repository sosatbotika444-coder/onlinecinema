# SexParty

SexParty is a watch-party web service for private synchronized movie rooms. The project is a monorepo with a FastAPI backend and a React/Vite frontend.

## Stack

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, Redis, python-socketio, S3-compatible uploads
- Frontend: React, TypeScript, Vite, Tailwind CSS, Framer Motion, Socket.IO client
- Local infra: Docker Compose with PostgreSQL, Redis, MinIO, Nginx
- Deploy targets: Railway for backend, Netlify for frontend

## Local Development

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Nginx proxy: http://localhost:8080
- MinIO console: http://localhost:9001

## Railway Backend Variables

Set these on the Railway backend service. Railway PostgreSQL should provide `DATABASE_URL`; Redis can be attached as a Railway Redis service.

```env
APP_NAME=SexParty API
ENVIRONMENT=production
API_PUBLIC_URL=https://your-backend.up.railway.app
FRONTEND_URL=https://your-site.netlify.app
CORS_ORIGINS=https://your-site.netlify.app
SESSION_SECRET=replace-with-a-long-random-secret
AUTO_CREATE_TABLES=true
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
MAX_UPLOAD_SIZE_MB=2048
S3_ENDPOINT_URL=https://your-s3-endpoint
S3_REGION=us-east-1
S3_BUCKET=sexparty
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_PUBLIC_BASE_URL=https://your-public-bucket-url
```

Railway should use `backend/railway.toml` with `backend/Dockerfile`. If the service is created from the monorepo root, set the Railway root directory to `backend`.

## Netlify Frontend Variables

The root `netlify.toml` builds from `frontend`, runs `npm run build`, and publishes `frontend/dist`.

```env
VITE_API_URL=https://your-backend.up.railway.app
VITE_SOCKET_URL=https://your-backend.up.railway.app
```

## Notes

- Uploaded files and direct mp4/webm links use native HTML5 sync.
- YouTube uses the IFrame API for playback state sync.
- VK Видео and Rutube are embedded best-effort because provider iframe controls do not expose consistent realtime control APIs.
