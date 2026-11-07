# Deploy: Google Cloud Run + twinbuild.click

One container serves everything from one origin: FastAPI (`api/main.py`) answers `/api/*` and serves the built three.js
viewer (`web/dist`: `/`, `/capture.html`, `/assets/*`, the `web/public` files). Both exports are baked into the image:
`data/derived/viewer/` (the manual build), `data/derived/viewer_auto/` (the automatic build) and
`data/derived/compare.json`, each export as `scene.json`, `scene.bin` (for the snapshot page) and `lod/` (the detail
levels the viewer streams, points and splats). The step images are **not** in the image: `/api/images/{name}` sends the
browser to the public copy in this repository (`images/` as they are, the automatic build's pictures as the JPEG sample
in `autoscene/out/samples/`), see `A2B_IMAGE_FALLBACK` in `api/main.py`.

| Part | Choice |
|---|---|
| Project | `twinbuild-a2b`, billing account *Firebase Payment* |
| Region | `europe-north1` (Finland) |
| Service | Cloud Run `a2b`: 1 vCPU, 512 MiB, min 0 / **max 1** instance, public (`allUsers` → `run.invoker`) |
| Live URL | https://twinbuild.click/ (service URL https://a2b-aj7gruyyjq-lz.a.run.app) |
| Images | Artifact Registry `europe-north1-docker.pkg.dev/twinbuild-a2b/a2b/a2b`, keeps the 5 newest |
| Exports | private bucket `gs://twinbuild-a2b-scene/` with `viewer/`, `viewer_auto/`, `compare.json` (not in git; Cloud Build copies them into the image) |
| Identities | `a2b-run` (runtime, **no roles**: it only serves files), `a2b-build` (Cloud Build: run.developer, artifact writer, log writer, object viewer, actAs a2b-run) |
| Cost guard | budget alert **3 EUR** on the project (e-mails at 50 / 90 / 100 %), max 1 instance, scale to zero |

## Day to day

```bash
make publish-scene     # after accepting parts or a new autoscene run: export both builds + the comparison, upload (~1 min)
make deploy            # Cloud Build: exports from the bucket -> image -> Cloud Run (~3 min)
```

`publish-scene` needs the scan on this machine (`make viewer`, `make viewer-auto`, `make compare` run first) and a
logged-in `gcloud`. `deploy` needs only `gcloud`: the build runs inside Google as `a2b-build`. The code that goes live
is the checkout you run `make deploy` in (uploaded as the build source), so run it on `main` after merging.

Local check of the exact image: `make viewer viewer-auto compare && make docker-build && make docker-run` →
http://localhost:8080. `make test T=api` runs the API tests (temp folders, no export needed).

## Deploy on every merge to main (GitHub Actions -> Cloud Build -> Cloud Run)

`.github/workflows/deploy.yml` runs the same `make deploy` on every push to `main` that changes something in the image
(`api/`, `web/`, `design/`, `Dockerfile`, `cloudbuild.yaml`, `Makefile`; README and docs changes don't deploy), and
on *Run workflow* in the Actions tab. The job signs in to Google Cloud as `a2b-build` with **Workload Identity
Federation**: GitHub's OIDC token for this repository is exchanged for the service account, so no key is stored in
GitHub or anywhere else, and only `Haaparanta/SinceAI_2026_Valmet` can use the pool. Cloud Build then builds the image
from the bucket's exports and deploys it, exactly as from the laptop. `make publish-scene` stays the way to update
the exports.

One-time cloud setup (idempotent, needs a logged-in `gcloud` with owner rights on the project):

```bash
make deploy-github     # scripts/gcp_github_deploy.sh: WIF pool `github` + provider, IAM for a2b-build, staging bucket
```

What it grants: the repo's workflows get `workloadIdentityUser` on `a2b-build`; `a2b-build` gets
`cloudbuild.builds.editor` + `logging.viewer` on the project, `serviceAccountUser` on itself (to submit builds that run
as itself) and `objectAdmin` on the source staging bucket `gs://twinbuild-a2b_cloudbuild` (sources are deleted after
a day). The provider path in the workflow is `projects/566541224410/locations/global/workloadIdentityPools/github/providers/github`
(566541224410 is the project number). Watch a run: `gh run list --workflow deploy` / `gh run watch`.

Alternative without GitHub Actions: a Cloud Build trigger (`make deploy-trigger`) after connecting the repository once
in the console (Cloud Build → *Triggers* → *Connect repository* → GitHub, needs your browser).

## Site files (web/public)

Copied as-is to the site root by Vite: `favicon.ico` / `favicon.svg` / `apple-touch-icon.png` / `icon-192.png` /
`icon-512.png`, `site.webmanifest`, `robots.txt` (blocks `/api/` and `/capture.html`), `sitemap.xml` (update
`<lastmod>` after big changes) and `og-image.jpg`, the 1200×630 link preview. Re-render the preview with
`cd web && node tools/snap.mjs --file public/og-image.png "src=overlay&part=process_pump_1&frame=room&dollhouse=1&size=1200x630&legend=0&textscale=2.6&title=…"`
and convert to JPEG. `tests/test_web_public.py` checks that the page head only references files that exist.

## One-time setup (already done on 2026-11-07)

```bash
gcloud auth login
PROJECT=twinbuild-a2b BILLING=016006-7A3E8F-0113DB scripts/gcp_setup.sh    # idempotent
make publish-scene && make deploy
gcloud run services add-iam-policy-binding a2b --region europe-north1 --project twinbuild-a2b \
  --member=allUsers --role=roles/run.invoker
```

## Custom domain twinbuild.click (Porkbun)

1. **Buy** `twinbuild.click` at porkbun.com. Turn **auto-renew off**, keep **WHOIS privacy on**.
2. **Verify ownership with Google** (once per Google account):
   `gcloud domains verify twinbuild.click` opens Search Console → choose *Domain*, copy the `google-site-verification`
   TXT value → Porkbun: *Domain Management → DNS* → add `TXT` record, host empty, that value → back in Search Console
   press *Verify*. `gcloud domains list-user-verified` must then list `twinbuild.click`.
3. **Map it to the service**:
   ```bash
   gcloud beta run domain-mappings create --service a2b --domain twinbuild.click \
     --region europe-north1 --project twinbuild-a2b
   gcloud beta run domain-mappings describe --domain twinbuild.click \
     --region europe-north1 --project twinbuild-a2b --format='table(status.resourceRecords)'
   ```
4. **DNS at Porkbun**: first **delete the parking records** (`A`/`ALIAS`/`CNAME` pointing to `207.207.210.x` or
   `pixie.porkbun.com`), then add the 4 `A` and 4 `AAAA` records from step 3 with an empty host. Keep the TXT record.
5. Google issues the HTTPS certificate by itself, usually within 15–60 min. `describe` shows `CertificateProvisioned: True`.

Domain mappings are free (the load-balancer alternative costs ~18 USD/month).

## Costs and teardown

Idle cost is close to zero: Cloud Run scales to zero, the bucket holds a few hundred MB, and Artifact Registry keeps at
most 5 images that share their base layers. The real cost driver is egress: a full page load of one build streams
about 30 MB of points (plus about 50 MB of splats when Splats is switched on), so 100 visits ≈ 3–8 GB of internet
egress, billed per GB; the step images come from GitHub and cost nothing here. Watch *Billing → Reports*; the 3 EUR
budget e-mails you long before it matters.

Teardown after the hackathon: `gcloud projects delete twinbuild-a2b` (deletes everything, 30-day undo), then delete
the budget in *Billing → Budgets & alerts*, and let the domain expire (auto-renew is off).
