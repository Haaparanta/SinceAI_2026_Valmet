# a2b - Approve-to-Build Twin (Valmet x Since AI 2026). See AGENTS.md S1 "Bootstrap".
# Targets: setup | pipeline | api | web | check | demo | timelapse | viewer | snap
#          docker-build | docker-run | gcp-setup | publish-scene | deploy   (docs/DEPLOY.md)
.PHONY: setup pipeline api web check demo lint test contracts timelapse viewer snap gcp-setup publish-scene deploy docker-build docker-run help
UV ?= uv
PY := $(UV) run python

help:            ## list targets
	@grep -E '^[a-zA-Z_/.-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | sort

setup:           ## Python 3.12 venv + deps (uv), web deps (npm), data/raw symlink
	$(UV) python install 3.12
	$(UV) sync
	cd web && npm install
	@$(MAKE) --no-print-directory data/raw

data/raw:        ## symlink to the read-only partner folder (relative; the .ply/.mp4 are gitignored)
	@test -e data/raw || ln -s ../Source-Data-Do-Not_change data/raw

data/derived/scene_points.bin data/derived/clean.npz: pipeline/01_clean.py pipeline/common/ply_io.py | data/raw
	$(PY) pipeline/01_clean.py

data/derived/assets.json: pipeline/05_bind_metadata.py | data/raw
	$(PY) pipeline/05_bind_metadata.py --dump

pipeline: data/derived/scene_points.bin data/derived/assets.json   ## M1 clean + M6 xlsx dump (cached by make)

contracts:       ## export contracts/json-schema/*.json from the pydantic models
	$(PY) scripts/check_contracts.py

lint:            ## ruff
	$(UV) run ruff check .

test:            ## pytest
	$(UV) run pytest -q

check:           ## lint + contract drift + tests + web typecheck/build  (must be green before hand-off)
	$(UV) run ruff check .
	$(PY) scripts/check_contracts.py --check
	$(UV) run pytest -q
	cd web && npm run typecheck && npm run build

timelapse:       ## equipment-room images (else images/) -> docs/timelapse.mp4 (30-60 s); pass ARGS="--first 7 --hold-last 3" etc.
	$(UV) run --group video python scripts/timelapse.py $(ARGS)

api:             ## FastAPI on :8000 (reload)
	$(UV) run uvicorn api.main:app --reload --port 8000

web:             ## Vite dev server on :5173
	cd web && npm run dev

viewer:          ## build/manifest.json + part indices -> data/derived/viewer/scene.{bin,json} for web/ (seconds)
	$(PY) scripts/export_viewer_scene.py

snap:            ## capture.html views -> images/NNNN_*.png via headless Chrome; needs `make web`; Q="src=overlay&part=pipe_3" ...
	cd web && node tools/snap.mjs $(if $(SNAP_URL),--url $(SNAP_URL)) $(foreach q,$(Q),"$(q)")

# --- container + Google Cloud Run (docs/DEPLOY.md) -------------------------------------------------------------------
PROJECT ?= twinbuild-a2b
BUILD_SA = projects/$(PROJECT)/serviceAccounts/a2b-build@$(PROJECT).iam.gserviceaccount.com

docker-build:    ## image with API + built viewer + scene (run `make viewer` first)
	docker build -t a2b:local .

docker-run:      ## run the local image on http://localhost:8080
	docker run --rm -p 8080:8080 a2b:local

gcp-setup:       ## one-time Google Cloud setup: PROJECT=twinbuild-a2b BILLING=<billing account id>
	PROJECT=$(PROJECT) scripts/gcp_setup.sh

publish-scene: viewer  ## export the build and upload scene.{bin,json} to the private scene bucket
	gcloud storage cp data/derived/viewer/scene.bin data/derived/viewer/scene.json \
	  gs://$(PROJECT)-scene/viewer/ --project $(PROJECT)

deploy:          ## Cloud Build: scene from the bucket -> image -> Cloud Run europe-north1 (same as the main trigger)
	gcloud beta builds submit --project $(PROJECT) --config cloudbuild.yaml --service-account $(BUILD_SA) .

demo: pipeline   ## pipeline (cached) + API + web, Demo Mode on
	DEMO_MODE=1 $(UV) run uvicorn api.main:app --port 8000 & PID=$$!; trap "kill $$PID" EXIT; cd web && npm run dev
