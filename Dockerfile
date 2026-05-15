FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/out /app/backend/static

RUN mkdir -p /app/backend/data

EXPOSE 8000

# Shell-form CMD so $PORT (set by Railway / Fly / Heroku / etc.)
# interpolates; falls back to 8000 for local Docker. Runs as root
# inside the container — the PaaS-level sandbox is the security
# boundary, and Railway-mounted volumes are root-owned by default
# (a non-root UID would hit permission-denied on first DB write).
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
