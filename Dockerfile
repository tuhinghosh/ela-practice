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
COPY frontend/src/content/ /app/backend/content/
COPY --from=frontend-build /app/frontend/out /app/backend/static

RUN useradd -m appuser && mkdir -p /app/backend/data && chown -R appuser:appuser /app/backend/data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
