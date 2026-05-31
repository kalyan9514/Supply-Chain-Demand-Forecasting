#!/usr/bin/env bash
set -e

PROJECT_ID="${GCP_PROJECT_ID}"
REPO_NAME="${ARTIFACT_REGISTRY_NAME:-airflow-docker-image}"
IMAGE_NAME="${DOCKER_IMAGE_NAME:-data-pipeline}"
IMAGE_TAG=$(date +'%Y%m%d-%H%M%S')
GCP_LOCATION="${GCP_LOCATION:-us-central1}"
REPO_URI="${GCP_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

echo "Building image: ${REPO_URI}/${IMAGE_NAME}:${IMAGE_TAG}"

docker build --no-cache \
  -t "${REPO_URI}/${IMAGE_NAME}:${IMAGE_TAG}" \
  -f Data_Pipeline/Dockerfile Data_Pipeline

docker tag "${REPO_URI}/${IMAGE_NAME}:${IMAGE_TAG}" "${REPO_URI}/${IMAGE_NAME}:latest"

docker push "${REPO_URI}/${IMAGE_NAME}:${IMAGE_TAG}"
docker push "${REPO_URI}/${IMAGE_NAME}:latest"

echo "Image pushed: ${IMAGE_TAG}"