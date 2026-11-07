#!/usr/bin/env bash
# One-time: let GitHub Actions deploy on every merge to main (idempotent: safe to re-run). Needs `gcloud auth login`.
#
#   PROJECT=twinbuild-a2b scripts/gcp_github_deploy.sh
#
# No keys anywhere: GitHub's OIDC token for this repository is exchanged (Workload Identity Federation) for the
# a2b-build service account, which then runs `make deploy` = `gcloud builds submit cloudbuild.yaml`, exactly like the
# laptop does. The build itself still runs inside Cloud Build as a2b-build and deploys to Cloud Run. See docs/DEPLOY.md
# and .github/workflows/deploy.yml.
set -euo pipefail

PROJECT="${PROJECT:-twinbuild-a2b}"
REGION="${REGION:-europe-north1}"
GITHUB_REPO="${GITHUB_REPO:-Haaparanta/SinceAI_2026_Valmet}"
POOL=github
PROVIDER=github
BUILD_SA="a2b-build@${PROJECT}.iam.gserviceaccount.com"
STAGING="gs://${PROJECT}_cloudbuild"   # where `gcloud builds submit` uploads the source
g() { gcloud --project "$PROJECT" --quiet "$@"; }
say() { printf '\n== %s\n' "$*"; }

NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"

say "APIs for token exchange"
g services enable iamcredentials.googleapis.com sts.googleapis.com

say "workload identity pool $POOL + provider $PROVIDER (only $GITHUB_REPO may use it)"
g iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1 \
  || g iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions"
g iam workload-identity-pools providers describe "$PROVIDER" --location=global --workload-identity-pool="$POOL" \
    >/dev/null 2>&1 \
  || g iam workload-identity-pools providers create-oidc "$PROVIDER" --location=global \
       --workload-identity-pool="$POOL" --display-name="GitHub" \
       --issuer-uri="https://token.actions.githubusercontent.com" \
       --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
       --attribute-condition="assertion.repository == '${GITHUB_REPO}'"

say "the repository's workflows may act as $BUILD_SA"
g iam service-accounts add-iam-policy-binding "$BUILD_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

say "$BUILD_SA may submit builds (as itself) and read their logs"
for role in roles/cloudbuild.builds.editor roles/logging.viewer; do
  g projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$BUILD_SA" --role="$role" \
    --condition=None >/dev/null
done
g iam service-accounts add-iam-policy-binding "$BUILD_SA" --member="serviceAccount:$BUILD_SA" \
  --role=roles/iam.serviceAccountUser >/dev/null

say "source staging bucket $STAGING (sources deleted after 1 day)"
g storage buckets describe "$STAGING" >/dev/null 2>&1 \
  || g storage buckets create "$STAGING" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
lifecycle="$(mktemp)"
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":1}}]}' >"$lifecycle"
g storage buckets update "$STAGING" --lifecycle-file="$lifecycle" >/dev/null
rm -f "$lifecycle"
g storage buckets add-iam-policy-binding "$STAGING" --member="serviceAccount:$BUILD_SA" \
  --role=roles/storage.objectAdmin >/dev/null

say "done. The workflow needs:"
echo "  workload_identity_provider: projects/${NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"
echo "  service_account: ${BUILD_SA}"
