# Backend-only image. The frontend is a static build (Vercel/Netlify), so it
# does not need a container - see README.md "Deployment" for why.
FROM python:3.12-slim

WORKDIR /srv

# Root-level ingestion modules (fetch_jobs.py, models.py, parsers/) are
# imported by backend/app, so they need to be in the image too.
COPY models.py fetch_jobs.py ./
COPY parsers/ ./parsers/
COPY backend/requirements.txt ./backend/requirements.txt
COPY backend/app/ ./backend/app/

RUN pip install --no-cache-dir -r backend/requirements.txt

ENV DATABASE_PATH=/srv/data/jobs.db
RUN mkdir -p /srv/data

EXPOSE 8000
WORKDIR /srv/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
