# SexParty

SexParty is a watch-party web service for private synchronized movie rooms. The project is a monorepo with a FastAPI backend and a React/Vite frontend.

## Stack

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, python-socketio, local backend uploads
- Frontend: React, TypeScript, Vite, Tailwind CSS, Framer Motion, Socket.IO client
- Local infra: Docker Compose with PostgreSQL and Nginx
- Deploy targets: Railway for backend, Netlify for frontend

## Local Development

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Nginx proxy: http://localhost:8080
## Railway Backend Variables

Set these on the Railway backend service. Railway PostgreSQL should provide `DATABASE_URL`.

```env
APP_NAME=SexParty API
ENVIRONMENT=production
API_PUBLIC_URL=https://your-backend.up.railway.app
FRONTEND_URL=https://your-site.netlify.app
CORS_ORIGINS=https://your-site.netlify.app
SESSION_SECRET=replace-with-a-long-random-secret
AUTO_CREATE_TABLES=true
DATABASE_URL=${{Postgres.DATABASE_URL}}
MAX_UPLOAD_SIZE_MB=2048
LOCAL_UPLOAD_DIR=uploads
```

Railway can deploy the backend directly from the repository root. The root `railway.toml` uses the root `Dockerfile`, which copies and runs the `backend/` app.

If you prefer Railway's isolated monorepo setup, you can instead set the service Root Directory to `/backend` and config path to `/backend/railway.toml`.

Local file uploads work without S3. On Railway this storage is ephemeral, so uploaded videos can disappear after redeploys/restarts. For production persistence, add S3-compatible storage later and install `boto3`.

## Netlify Frontend Variables

The root `netlify.toml` builds from `frontend`, runs `npm run build`, and publishes `frontend/dist`.

```env
VITE_API_URL=https://onlinecinema-production.up.railway.app
VITE_SOCKET_URL=https://onlinecinema-production.up.railway.app
```

## Notes

- Uploaded files and direct mp4/webm links use native HTML5 sync.
- YouTube uses the IFrame API for playback state sync.
- VK Видео and Rutube are embedded best-effort because provider iframe controls do not expose consistent realtime control APIs.
