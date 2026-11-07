# a2b - Approve-to-Build Twin (Valmet x Since AI 2026). See AGENTS.md S1 "Bootstrap".
# Targets: setup | pipeline | api | web | web-vr | check | demo | timelapse | viewer | snap | test (T=/K= to pick) | test-list | test-pick | test-changed | test-failed | test-web | viewer-fixture
.PHONY: setup pipeline api web web-vr check demo lint test test-list test-pick test-changed test-failed test-web viewer-fixture contracts timelapse viewer snap help
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

api:             ## FastAPI on :8000 (reload)
	$(UV) run uvicorn api.main:app --reload --port 8000

web:             ## Vite dev server on :5173
	cd web && npm run dev

web-vr:          ## Vite over HTTPS on all interfaces: open https://<this-ip>:5173 in Quest Browser, then Enter VR
	cd web && npm run dev:vr

viewer-fixture:  ## synthetic data/derived/viewer/scene.{bin,json} from build/manifest.json (no .ply needed; never replaces a real export)
	$(PY) scripts/make_viewer_fixture.py

test-web:        ## browser tests: viewer + capture.html in headless Chromium (own Vite on :5199); fixture if no export yet
	@test -f data/derived/viewer/scene.json || $(PY) scripts/make_viewer_fixture.py
	node --test --test-reporter=spec tests/web/*.test.mjs

viewer:          ## build/manifest.json + part indices -> data/derived/viewer/scene.{bin,splat,json} for web/ (seconds)
	$(PY) scripts/export_viewer_scene.py

snap:            ## capture.html views -> images/NNNN_*.png via headless Chrome; needs `make web`; Q="src=overlay&part=pipe_3" ...
	cd web && node tools/snap.mjs $(if $(SNAP_URL),--url $(SNAP_URL)) $(foreach q,$(Q),"$(q)")

demo: pipeline   ## pipeline (cached) + API + web, Demo Mode on
	DEMO_MODE=1 $(UV) run uvicorn api.main:app --port 8000 & PID=$$!; trap "kill $$PID" EXIT; cd web && npm run dev

viewer-auto:     ## autoscene/out (automatic build) -> data/derived/viewer_auto/scene.{bin,splat,json}; open the viewer with ?scene=auto
	$(PY) scripts/export_autoscene_viewer.py
