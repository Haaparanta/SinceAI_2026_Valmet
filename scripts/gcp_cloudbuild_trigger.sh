#!/usr/bin/env bash
# One-time: a Cloud Build trigger that builds + deploys on every merge to main (idempotent: safe to re-run).
# Needs `gcloud auth login` with owner rights on the project. Does not use GitHub Actions.
#
#   PROJECT=twinbuild-a2b scripts/gcp_cloudbuild_trigger.sh        # = make deploy-trigger
#
# 1. the Cloud Build service agent may store the GitHub token (Secret Manager)
# 2. a Cloud Build "GitHub" connection: prints ONE link; open it, install the Cloud Build GitHub app on the repository
#    (the script waits until you have)
# 3. the repository is linked to the connection
# 4. trigger `deploy-main`: cloudbuild.yaml on pushes to main that change the image inputs, run as a2b-build
# See docs/DEPLOY.md.
set -euo pipefail

PROJECT="${PROJECT:-twinbuild-a2b}"
REGION="${REGION:-europe-north1}"
OWNER="${OWNER:-Haaparanta}"
REPO_NAME="${REPO_NAME:-SinceAI_2026_Valmet}"
CONNECTION=github
LINK=a2b                                   # the linked-repository resource name
TRIGGER=deploy-main
BUILD_SA="projects/${PROJECT}/serviceAccounts/a2b-build@${PROJECT}.iam.gserviceaccount.com"
g() { gcloud --project "$PROJECT" --quiet "$@"; }
say() { printf '\n== %s\n' "$*"; }

NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
AGENT="service-${NUMBER}@gcp-sa-cloudbuild.iam.gserviceaccount.com"

say "APIs"
g services enable cloudbuild.googleapis.com secretmanager.googleapis.com

say "Cloud Build service agent may keep the GitHub token in Secret Manager"
g projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${AGENT}" \
  --role=roles/secretmanager.admin --condition=None >/dev/null

say "connection $CONNECTION ($REGION)"
if ! g builds connections describe "$CONNECTION" --region="$REGION" >/dev/null 2>&1; then
  g builds connections create github "$CONNECTION" --region="$REGION" --async >/dev/null
fi
while :; do
  read -r stage uri < <(g builds connections describe "$CONNECTION" --region="$REGION" \
    --format='value(installationState.stage,installationState.actionUri)' 2>/dev/null || echo "CREATING -")
  case "$stage" in
    COMPLETE) echo "connection installed"; break ;;
    PENDING_CREATE_APP|PENDING_USER_OAUTH|PENDING_INSTALL_APP)
      printf '\n  >>> open this link, sign in to GitHub and install the Cloud Build app on %s/%s, then come back:\n  %s\n\n' \
        "$OWNER" "$REPO_NAME" "$uri"
      printf '  waiting'
      while read -r s _ < <(g builds connections describe "$CONNECTION" --region="$REGION" \
          --format='value(installationState.stage,installationState.actionUri)'); [ "$s" != COMPLETE ]; do
        printf '.'; sleep 5
      done
      echo; echo "connection installed"; break ;;
    *) printf '  state %s, waiting\n' "$stage"; sleep 5 ;;
  esac
done

say "repository $OWNER/$REPO_NAME linked as $LINK"
g builds repositories describe "$LINK" --connection="$CONNECTION" --region="$REGION" >/dev/null 2>&1 \
  || g builds repositories create "$LINK" --connection="$CONNECTION" --region="$REGION" \
       --remote-uri="https://github.com/${OWNER}/${REPO_NAME}.git" >/dev/null

say "trigger $TRIGGER: cloudbuild.yaml on pushes to main, as a2b-build"
REPO_RES="projects/${PROJECT}/locations/${REGION}/connections/${CONNECTION}/repositories/${LINK}"
FILES='api/**,web/**,design/**,Dockerfile,.dockerignore,.gcloudignore,cloudbuild.yaml,Makefile'
if g builds triggers describe "$TRIGGER" --region="$REGION" >/dev/null 2>&1; then
  g builds triggers delete "$TRIGGER" --region="$REGION" >/dev/null
fi
g builds triggers create github --name="$TRIGGER" --region="$REGION" --repository="$REPO_RES" \
  --branch-pattern='^main$' --build-config=cloudbuild.yaml --service-account="$BUILD_SA" \
  --included-files="$FILES" --description="deploy twinbuild.click on every merge to main" >/dev/null

g builds triggers describe "$TRIGGER" --region="$REGION" --format='yaml(name,github,repositoryEventConfig,filename,serviceAccount,includedFiles)'
say "done: every push to main that changes the image inputs now builds and deploys. Try one: make deploy-trigger-run"
