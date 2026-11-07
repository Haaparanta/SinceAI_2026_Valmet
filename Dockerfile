# a2b - Approve-to-Build Twin: one container = FastAPI (api/) + the built three.js viewer (web/dist) + the scene.
#
#   make viewer && make docker-build && make docker-run        # local: http://localhost:8080
#   make deploy                                                  # Cloud Build -> Artifact Registry -> Cloud Run
#
# The scene (data/derived/viewer/scene.{bin,json}) is not in git: locally it comes from `make viewer`, in Cloud Build
# from the scene bucket (cloudbuild.yaml step 1). Both put it in the build context at the same path.

# ---- 1. build the viewer -----------------------------------------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /src
COPY web/package.json web/package-lock.json web/
RUN cd web && npm ci --no-audit --no-fund
COPY design/ design/
COPY web/ web/
RUN cd web && npm run build

# ---- 2. runtime ----------------------------------------------------------------------------------------------------
FROM python:3.12-slim
# pip installs system-wide as root on purpose: this image runs one app, as the unprivileged user below
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
# same versions as uv.lock; only what api/main.py imports
RUN pip install "fastapi==0.162.0" "starlette==1.10.0" "uvicorn[standard]==0.54.0"
WORKDIR /app
COPY api/ api/
COPY --from=web /src/web/dist web/dist
COPY data/derived/viewer/scene.bin data/derived/viewer/scene.json data/derived/viewer/
# served as Content-Encoding: gzip to browsers that accept it (29 MB -> 23 MB on the wire)
RUN gzip -9 -k data/derived/viewer/scene.bin \
 && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin app
USER app
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
