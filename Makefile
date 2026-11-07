# a2b - Approve-to-Build Twin (Valmet x Since AI 2026). See AGENTS.md S1 "Bootstrap".
# Targets: setup | pipeline | api | web | web-vr | check | demo | timelapse | media | demo-video | viewer | viewer-auto | compare | snap | test (T=/K= to pick) | test-list | test-pick | test-changed | test-failed | test-web | viewer-fixture | docker-build | docker-run | publish-scene | deploy | deploy-trigger | deploy-trigger-run | deploy-github (docs/DEPLOY.md)
.PHONY: setup pipeline api web web-vr check demo demo-video lint test test-list test-pick test-changed test-failed test-web viewer-fixture compare contracts timelapse media viewer viewer-auto snap help docker-build docker-run gcp-setup publish-scene deploy deploy-trigger deploy-trigger-run deploy-github
UV ?= uv
PY := $(UV) run python
# Google Cloud (docs/DEPLOY.md): the project, the Cloud Build account and the private bucket that holds the exports
PROJECT ?= twinbuild-a2b
BUILD_SA = projects/$(PROJECT)/serviceAccounts/a2b-build@$(PROJECT).iam.gserviceaccount.com
SCENE_BUCKET = gs://$(PROJECT)-scene

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

test:            ## pytest; pick some: T="parts cleaning" (files) T=parts::test_x  K=lamp (name match)  ARGS="-x -vv"
	$(PY) scripts/run_tests.py $(T) $(if $(K),-k "$(K)") $(if $(ARGS),-- $(ARGS))

test-list:       ## list test files + test names (what T= / K= can pick)
	@$(PY) scripts/run_tests.py --list

test-pick:       ## numbered menu: choose which test files to run
	@$(PY) scripts/run_tests.py --pick

test-changed:    ## only tests related to .py files changed vs origin/main (+ uncommitted)
	@$(PY) scripts/run_tests.py --changed

test-failed:     ## only the tests that failed last run
	@$(PY) scripts/run_tests.py --failed

check:           ## lint + contract drift + tests + web typecheck/build  (must be green before hand-off)
	$(UV) run ruff check .
	$(PY) scripts/check_contracts.py --check
	$(UV) run pytest -q
	cd web && npm run typecheck && npm run build

timelapse:       ## equipment-room images (else images/) -> docs/timelapse.mp4 (30-60 s); pass ARGS="--first 7 --hold-last 3" etc.
	$(UV) run --group video python scripts/timelapse.py $(ARGS)

media:           ## README videos + GIF previews of both builds from the committed images -> docs/media/ (no .ply needed)
	$(UV) run --group video python scripts/readme_media.py $(ARGS)

demo-video:      ## the two-minute demo video (video/README.md): narration (ElevenLabs key in video/.env) + captions + Remotion render -> video/out/a2b_demo.mp4
	cd video && npm install --no-audit --no-fund && node tools/narrate.mjs --voice Daniel --speed 1.06 && node tools/assets.mjs && node tools/srt.mjs && npx remotion render src/index.ts Demo out/a2b_demo.mp4 --codec h264 --crf 19

api:             ## FastAPI on :8000 (reload)
	$(UV) run uvicorn api.main:app --reload --port 8000

web:             ## Vite dev server on :5173
	cd web && npm run dev

web-vr:          ## Vite over HTTPS on all interfaces: open https://<this-ip>:5173 in Quest Browser, then Enter VR
	cd web && npm run dev:vr

viewer-fixture:  ## synthetic viewer exports for both builds (viewer/, viewer_auto/) from committed files (no .ply; never replaces a real export)
	$(PY) scripts/make_viewer_fixture.py

compare:         ## manual vs automatic build (committed boxes, no .ply) -> data/derived/compare.json + docs/build_comparison.md
	$(PY) scripts/compare_builds.py

test-web:        ## browser tests: viewer + capture.html in headless Chromium (own Vite on :5199); fixtures for builds with no export
	@$(PY) scripts/make_viewer_fixture.py --missing-only
	@test -f data/derived/compare.json || $(PY) scripts/compare_builds.py --no-report
	node --test --test-reporter=spec tests/web/*.test.mjs

viewer:          ## build/manifest.json + part indices -> data/derived/viewer/scene.{bin,splat,json} + lod/ (detail levels) for web/ (seconds)
	$(PY) scripts/export_viewer_scene.py

snap:            ## capture.html views -> images/NNNN_*.png via headless Chrome; needs `make web`; Q="src=overlay&part=pipe_3" ...
	cd web && node tools/snap.mjs $(if $(SNAP_URL),--url $(SNAP_URL)) $(foreach q,$(Q),"$(q)")

demo: pipeline   ## pipeline (cached) + API + web, Demo Mode on
	DEMO_MODE=1 $(UV) run uvicorn api.main:app --port 8000 & PID=$$!; trap "kill $$PID" EXIT; cd web && npm run dev

viewer-auto:     ## autoscene/out (automatic build) -> data/derived/viewer_auto/scene.{bin,splat,json} + lod/; open the viewer with ?scene=auto
	$(PY) scripts/export_autoscene_viewer.py

# ---- the website: one container on Cloud Run, https://twinbuild.click (docs/DEPLOY.md) ----
docker-build:    ## image with API + built viewer + both exports (run `make viewer viewer-auto compare` first)
	docker build -t a2b:local .

docker-run:      ## run the local image on http://localhost:8080
	docker run --rm -p 8080:8080 a2b:local

gcp-setup:       ## one-time Google Cloud setup: PROJECT=twinbuild-a2b BILLING=<billing account id>
	PROJECT=$(PROJECT) scripts/gcp_setup.sh

publish-scene: viewer viewer-auto compare  ## export both builds + the comparison and upload them to the private scene bucket
	gcloud storage rsync -r --exclude='scene\.splat$$' data/derived/viewer $(SCENE_BUCKET)/viewer --project $(PROJECT)
	gcloud storage rsync -r --exclude='scene\.splat$$' data/derived/viewer_auto $(SCENE_BUCKET)/viewer_auto --project $(PROJECT)
	gcloud storage cp data/derived/compare.json $(SCENE_BUCKET)/compare.json --project $(PROJECT)

deploy:          ## Cloud Build: exports from the bucket -> image -> Cloud Run europe-north1 (what the deploy-main trigger does on merge to main)
	gcloud beta builds submit --project $(PROJECT) --config cloudbuild.yaml --service-account $(BUILD_SA) .

deploy-trigger:  ## one-time: build + deploy on every merge to main (Cloud Build trigger; opens one GitHub link). docs/DEPLOY.md
	PROJECT=$(PROJECT) scripts/gcp_cloudbuild_trigger.sh

deploy-trigger-run:  ## run the main trigger now (same as a merge to main)
	gcloud builds triggers run deploy-main --region europe-north1 --branch main --project $(PROJECT)

deploy-github:   ## alternative when GitHub Actions is available: WIF for a workflow that runs `make deploy` (see docs/DEPLOY.md)
	PROJECT=$(PROJECT) scripts/gcp_github_deploy.sh
