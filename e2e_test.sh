#!/bin/bash
# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
# Usage
# =====
#
# FRONTEND_REPO="https://github.com/tergite/tergite-frontend.git" \
#   BACKEND_REPO="https://github.com/tergite/tergite-backend.git" \
#   BACKEND_BRANCH="main" \ # you can set a different backend branch; default is 'main'
#   FRONTEND_BRANCH="main" \ # you can set a different frontend branch; default is 'main'
#   DEBUG="True" \ # Set 'True' to avoid cleaning up the containers, env, and repos after test, default: ''
#   PYTHON_IMAGE="python:3.9-slim" \ # Set the docker image to run the tests. If not provided, it runs on the host machine
#   ./e2e_test.sh

set -e # exit if any step fails

# Global variables
TEMP_DIR="temp"
FRONTEND_REPO="$FRONTEND_REPO"
FRONTEND_BRANCH="${FRONTEND_BRANCH:-main}"
BACKEND_REPO="$BACKEND_REPO"
BACKEND_BRANCH="${BACKEND_BRANCH:-main}"
APP_TOKEN="pZTccp8F-8RLFvQie1AMM0ptfdkGNnH1wDEB4INUFqw"
ROOT_PATH="$(pwd)"
TEMP_DIR_PATH="$ROOT_PATH/$TEMP_DIR"
FIXTURES_PATH="$ROOT_PATH/tests/fixtures"
PYTHON_IMAGE="$PYTHON_IMAGE"

# Logging function for errors
log_error() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - ERROR: $1" >&2
}

# Clean up any remaining docker things
echo "Cleaning up docker artefacts from previous runs"
docker compose -p tergite-e2e  down --rmi all --volumes 2>/dev/null
docker rmi -f tergite/tergite-mss 2>/dev/null
docker rmi -f tergite/tergite-dashboard 2>/dev/null
docker rmi -f tergite/tergite-backend-e2e:latest 2>/dev/null
docker system prune -f

# Create and navigating to temporary directory
echo "Creating temp folder $TEMP_DIR_PATH"
rm -rf "$TEMP_DIR_PATH"
mkdir "$TEMP_DIR_PATH"
cd "$TEMP_DIR_PATH"

# Setting up the repositories
echo "Cloning repositories..."
rm -rf tergite-frontend
rm -rf tergite-backend
git clone --single-branch --branch "$FRONTEND_BRANCH" "$FRONTEND_REPO"
git clone --single-branch --branch "$BACKEND_BRANCH" "$BACKEND_REPO"

# Adding configuration files to tergite-frontend folder
echo "Adding configuration files"
cd tergite-frontend
cp "$FIXTURES_PATH/mongo-init.js" .
cp "$FIXTURES_PATH/e2e-docker-compose.yml" .
cp "$FIXTURES_PATH/qiskit_pulse_1q.toml" .
cp "$FIXTURES_PATH/qiskit_pulse_1q.seed.toml" .
cp "$FIXTURES_PATH/qiskit_pulse_2q.toml" .
cp "$FIXTURES_PATH/qiskit_pulse_2q.seed.toml" .
cp "$FIXTURES_PATH/private-mss-key.pem" .
cp "$FIXTURES_PATH/public-mss-key.pem" .
cp "$FIXTURES_PATH/e2e.env" .env
printf "\nMSS_APP_TOKEN=\"$APP_TOKEN\"" >> .env
cp "$FIXTURES_PATH/mss-config.toml" .


# Starting services in the tergite-frontend folder
echo "Starting all e2e services"
docker compose \
  -f fresh-docker-compose.yml\
  -f e2e-docker-compose.yml \
  -p tergite-e2e \
  up -d

# Run in python docker file if $PYTHON_IMAGE is set
# or else run on host machine

if [[ -z "$PYTHON_IMAGE" ]]; then
  # Starting the tests
  echo "Create virtual environment for tests..."
  rm -rf "$ROOT_PATH/env"
  python -m venv "$ROOT_PATH/env"
  LOCAL_PYTHON="$ROOT_PATH/env/bin/python"
  cd "$ROOT_PATH"
  "$LOCAL_PYTHON" -m pip install ."[test]"

  echo "Running end-to-end test suite..."
  IS_END_TO_END="True" \
   API_URL="http://127.0.0.1:8002" \
   API_TOKEN="$APP_TOKEN" \
   $LOCAL_PYTHON -m pytest "$ROOT_PATH/tests"
else
  cd "$ROOT_PATH"
  cp "$FIXTURES_PATH/e2e-runner.sh" .
  docker run \
    --name tergite-e2e-runner \
    --network=tergite-e2e_tergite-e2e \
    -v "$PWD":/app -w /app \
    -e APP_TOKEN="$APP_TOKEN" \
    -e API_URL="http://mss:8002" \
    "$PYTHON_IMAGE" bash ./e2e-runner.sh
fi

# Cleanup
# In order to debug the containers and the repos,
# set the env variable "DEBUG" to True
if [[ $(echo "${DEBUG}" | tr '[:lower:]' '[:upper:]') != "TRUE" ]]; then
  echo "Cleaning up..."
  docker compose -p tergite-e2e down --rmi all --volumes
  docker rm -f tergite-e2e-runner 2>/dev/null || true
  rm -rf "$TEMP_DIR_PATH" || true
  rm -rf "$ROOT_PATH/env" || true
  rm "$ROOT_PATH/e2e-runner.sh" || true
else
  echo "Not deleting the containers and repositories because DEBUG=$DEBUG"
fi

echo "Script completed."
