#!/usr/bin/env bash
# One-time Google Cloud setup for the a2b viewer (idempotent: safe to re-run). Needs `gcloud auth login` first.
#
#   PROJECT=twinbuild-a2b BILLING=XXXXXX-XXXXXX-XXXXXX scripts/gcp_setup.sh
#
# Creates: the project (linked to BILLING), the APIs, an Artifact Registry repo, a private scene bucket, two service
# accounts with least privilege, and a 3 EUR budget alert. Region europe-north1 (Finland). See docs/DEPLOY.md.
set -euo pipefail

PROJECT="${PROJECT:-twinbuild-a2b}"
BILLING="${BILLING:?set BILLING to the billing account id (gcloud billing accounts list)}"
REGION="${REGION:-europe-north1}"
REPO=a2b
BUCKET="gs://${PROJECT}-scene"
RUN_SA="a2b-run@${PROJECT}.iam.gserviceaccount.com"
BUILD_SA="a2b-build@${PROJECT}.iam.gserviceaccount.com"
BUDGET_EUR="${BUDGET_EUR:-3}"
g() { gcloud --project "$PROJECT" --quiet "$@"; }
say() { printf '\n== %s\n' "$*"; }

say "project $PROJECT"
gcloud projects describe "$PROJECT" >/dev/null 2>&1 || gcloud projects create "$PROJECT" --name="twinbuild a2b"
gcloud billing projects link "$PROJECT" --billing-account="$BILLING" >/dev/null

say "APIs"
g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  storage.googleapis.com iam.googleapis.com billingbudgets.googleapis.com cloudresourcemanager.googleapis.com

say "Artifact Registry repo $REPO ($REGION), keep only the 5 newest images"
g artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 \
  || g artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" \
       --description="a2b viewer images"
policy="$(mktemp)"
cat >"$policy" <<'JSON'
[{"name": "keep-5", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}},
 {"name": "delete-old", "action": {"type": "Delete"}, "condition": {"olderThan": "1d"}}]
JSON
g artifacts repositories set-cleanup-policies "$REPO" --location="$REGION" --policy="$policy" --no-dry-run >/dev/null
rm -f "$policy"

say "scene bucket $BUCKET (private; Cloud Build copies the scene into the image)"
g storage buckets describe "$BUCKET" >/dev/null 2>&1 \
  || g storage buckets create "$BUCKET" --location="$REGION" --uniform-bucket-level-access --public-access-prevention

say "service accounts"
g iam service-accounts describe "$RUN_SA" >/dev/null 2>&1 \
  || g iam service-accounts create a2b-run --display-name="a2b Cloud Run runtime (no roles: it only serves files)"
g iam service-accounts describe "$BUILD_SA" >/dev/null 2>&1 \
  || g iam service-accounts create a2b-build --display-name="a2b Cloud Build deployer"

say "IAM for the build account"
for role in roles/run.developer roles/logging.logWriter roles/storage.objectViewer; do
  g projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$BUILD_SA" --role="$role" \
    --condition=None >/dev/null
done
g artifacts repositories add-iam-policy-binding "$REPO" --location="$REGION" \
  --member="serviceAccount:$BUILD_SA" --role=roles/artifactregistry.writer >/dev/null
g iam service-accounts add-iam-policy-binding "$RUN_SA" \
  --member="serviceAccount:$BUILD_SA" --role=roles/iam.serviceAccountUser >/dev/null
# `gcloud builds submit` as this account: it must also act as itself and read the source upload bucket
g iam service-accounts add-iam-policy-binding "$BUILD_SA" \
  --member="user:$(gcloud config get-value account 2>/dev/null)" --role=roles/iam.serviceAccountUser >/dev/null

say "budget alert ${BUDGET_EUR} EUR (50 / 90 / 100 % e-mails to billing admins)"
# the Budget API is called with this project as quota project (not whatever gcloud defaults to)
if ! gcloud --billing-project="$PROJECT" billing budgets list --billing-account="$BILLING" --format='value(displayName)' 2>/dev/null \
     | grep -qx "a2b ${PROJECT}"; then
  number="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  gcloud --billing-project="$PROJECT" --quiet billing budgets create --billing-account="$BILLING" --display-name="a2b ${PROJECT}" \
    --budget-amount="${BUDGET_EUR}EUR" --filter-projects="projects/${number}" \
    --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
fi

say "done: next \`make publish-scene\` then \`make deploy\`"
