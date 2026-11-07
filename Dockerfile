# a2b - Approve-to-Build Twin: one container = FastAPI (api/) + the built three.js viewer (web/dist) + both exports.
#
#   make viewer viewer-auto compare && make docker-build && make docker-run   # local: http://localhost:8080
#   make deploy                                                                # Cloud Build -> Artifact Registry -> Cloud Run
#
# The exports (data/derived/viewer, data/derived/viewer_auto, data/derived/compare.json) are not in git: locally they
# come from the make targets above, in Cloud Build from the scene bucket (cloudbuild.yaml step 1). Both put them in the
# build context at the same paths. scene.splat stays out (the viewer streams lod/*.splat instead), and so do the step
# images: the API sends browsers to the public copy in the GitHub repository (api/main.py, A2B_IMAGE_FALLBACK).

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
# viewer/ and viewer_auto/ (scene.json, scene.bin, lod/) and compare.json; .dockerignore keeps everything else out
COPY data/derived/ data/derived/
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin app
USER app
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
