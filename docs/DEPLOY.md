# Deploy: Google Cloud Run + twinbuild.click

One container serves everything from one origin: FastAPI (`api/main.py`) answers `/api/*` and serves the built three.js
viewer (`web/dist`: `/`, `/capture.html`, `/assets/*`). The scene is baked into the image at
`data/derived/viewer/scene.{bin,json}`, with a pre-gzipped `scene.bin.gz` (29.1 MB → 23.0 MB on the wire).

| Part | Choice |
|---|---|
| Project | `twinbuild-a2b`, billing account *Firebase Payment* |
| Region | `europe-north1` (Finland) |
| Service | Cloud Run `a2b`: 1 vCPU, 512 MiB, min 0 / **max 1** instance, public (`allUsers` → `run.invoker`) |
| Live URL | https://a2b-aj7gruyyjq-lz.a.run.app (custom domain: see below) |
| Images | Artifact Registry `europe-north1-docker.pkg.dev/twinbuild-a2b/a2b/a2b`, keeps the 5 newest |
| Scene | private bucket `gs://twinbuild-a2b-scene/viewer/` (not in git; Cloud Build copies it into the image) |
| Identities | `a2b-run` (runtime, **no roles**: it only serves files), `a2b-build` (Cloud Build: run.developer, artifact writer, log writer, object viewer, actAs a2b-run) |
| Cost guard | budget alert **3 EUR** on the project (e-mails at 50 / 90 / 100 %), max 1 instance, scale to zero |

## Day to day

```bash
make publish-scene     # after accepting parts: export the build and upload scene.{bin,json} (~5 s)
make deploy            # Cloud Build: scene -> image -> Cloud Run (~2 min)
```

Local check of the exact image: `make viewer && make docker-build && make docker-run` → http://localhost:8080.

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

## Deploy on every push to main (optional)

The pipeline in `cloudbuild.yaml` is the same; only the trigger is missing. GitHub must be connected once in the
console (OAuth, needs your browser): Cloud Build → *Triggers* → *Connect repository* → GitHub → `Haaparanta/SinceAI_2026_Valmet`.
Then:

```bash
gcloud builds triggers create github --project twinbuild-a2b --region global --name deploy-main \
  --repo-owner Haaparanta --repo-name SinceAI_2026_Valmet --branch-pattern '^main$' \
  --build-config cloudbuild.yaml \
  --service-account projects/twinbuild-a2b/serviceAccounts/a2b-build@twinbuild-a2b.iam.gserviceaccount.com
```

No keys are stored anywhere: the build runs as `a2b-build`, inside Google.

## Costs and teardown

Idle cost is close to zero: Cloud Run scales to zero, the bucket holds 28 MB, and Artifact Registry keeps at most 5
images that share their base layers (a few hundred MB; storage above the 0.5 GB free tier costs cents per month).
The real cost driver is egress: each full page load sends ~23 MB to the visitor, so 100 visits ≈ 2.3 GB of internet
egress, billed per GB. Watch *Billing → Reports*; the 3 EUR budget e-mails you long before it matters.

Teardown after the hackathon: `gcloud projects delete twinbuild-a2b` (deletes everything, 30-day undo), then delete
the budget in *Billing → Budgets & alerts*, and let the domain expire (auto-renew is off).
