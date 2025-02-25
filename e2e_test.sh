#!/bin/bash

# Run backend
# Run frontend
# Run e2e tests

# Global variables
LOG_FILE="tergite_setup.log"
TEMP_DIR="temp"
FRONTEND_REPO="$FRONTEND_REPO"
FRONTEND_BRANCH="${FRONTEND_BRANCH:-main}"
BACKEND_REPO="$BACKEND_REPO"
BACKEND_BRANCH="${BACKEND_BRANCH:-main}"
APP_TOKEN="pZTccp8F-8RLFvQie1AMM0ptfdkGNnH1wDEB4INUFqw"
REDIS_PORT="6378"
MONGO_PORT="27018"
ROOT_PATH="$(pwd)"
TEMP_DIR_PATH="$ROOT_PATH/$TEMP_DIR"
DOCKER_NETWORK="tergite-e2e"
MAX_HTTP_RETRIES=5
HTTP_RETRY_INTERVAL=5

declare -a BACKENDS
BACKENDS[0]="qiskit_pulse_1q,8001"
BACKENDS[1]="qiskit_pulse_2q,8000"


# Logging function for errors
log_error() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - ERROR: $1" >&2
}

# Function to log messages
log_message() {
    local MSG="$1"
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $MSG" | tee -a "$LOG_FILE"
}

# Function to check for errors and exit if command fails
check_error() {
    if [ $? -ne 0 ]; then
        log_message "ERROR: $1"
        log_message "Exiting script."
        exit 1
    fi
}

# Prerequisite check: Git
log_message "Checking if Git is installed..."
if ! command -v git &> /dev/null; then
    log_message "Git is not installed. Please install Git and rerun the script."
    exit 1
fi

# Prerequisite check: Docker
log_message "Checking if Docker is installed..."
if ! command -v docker &> /dev/null; then
    log_message "Docker is not installed. Please install Docker and rerun the script."
    exit 1
fi

# Prerequisite check: python
log_message "Checking if python is installed..."
if ! command -v python &> /dev/null; then
    log_message "python is not installed. Please install python and rerun the script."
    exit 1
fi

# Create and navigate to temporary directory
log_message "Creating temporary working directory..."
rm -rf "$TEMP_DIR_PATH"
mkdir "$TEMP_DIR_PATH"
check_error "Failed to create or change into the $TEMP_DIR_PATH directory."

# Clean up any remaining docker things
log_message "Cleaning up docker containers from previous runs"
docker rm -f tergite-mongo 2>/dev/null
docker rm -f tergite-redis 2>/dev/null
docker compose -p tergite-frontend down --rmi all --volumes 2>/dev/null
for i in "${!BACKENDS[@]}"; do
  backend=$(echo "${BACKENDS[$i]}" | cut -d ',' -f 1)
  docker rm -f "$backend" 2>/dev/null
  check_error "Failed to cleanup backend container $backend."
done
check_error "Failed to cleanup containers."

log_message "Cleaning up docker images from previous runs"
docker rmi -f tergite/tergite-mss 2>/dev/null
docker rmi -f tergite/tergite-dashboard 2>/dev/null
docker rmi -f tergite-e2e/tergite-backend:latest 2>/dev/null
check_error "Failed to clean up all docker images."

log_message "Cleaning up docker networks from previous runs"
docker network rm "$DOCKER_NETWORK" 2>/dev/null
check_error "Failed to clean up all docker networks."

# Create the network to connect all these services
log_message "Creating the $DOCKER_NETWORK network"
docker network create "$DOCKER_NETWORK"
check_error "Failed to create docker network '$DOCKER_NETWORK'."

# Setup mongo database
log_message "Starting mongodb at port $MONGO_PORT"
cd "$TEMP_DIR_PATH"
cp "$ROOT_PATH/tests/fixtures/mongo-init.js" mongo-init.js
docker run --name tergite-mongo \
    -v "$(pwd)/mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro" \
    -p "$MONGO_PORT":27017 \
    --network "$DOCKER_NETWORK" \
    -d mongo
check_error "Failed to running mongodb."

# set up redis
log_message "Starting redis at port $REDIS_PORT"
cd "$TEMP_DIR_PATH"
docker run --name tergite-redis -p "$REDIS_PORT":6379 --network "$DOCKER_NETWORK" -d redis
check_error "Failed to running redis."

# Docker setup for frontend
log_message "Cloning frontend repository..."
cd "$TEMP_DIR_PATH"
rm -rf tergite-frontend
git clone --single-branch --branch "$FRONTEND_BRANCH" "$FRONTEND_REPO"
check_error "Failed to clone frontend repository."

# Set up the docker network for tergite frontend
log_message "Setting up docker network for frontend..."
cd "$TEMP_DIR_PATH/tergite-frontend"
# add network on mss
awk "/  mss:/ {print; print \"    networks:\n      - $DOCKER_NETWORK\"; next}1" fresh-docker-compose.yml > temp.yml && mv temp.yml fresh-docker-compose.yml
# add the external network in list of networks
echo "networks:" >> fresh-docker-compose.yml
echo "  $DOCKER_NETWORK:" >> fresh-docker-compose.yml
echo "    external: true" >> fresh-docker-compose.yml
check_error "Failed to set up $DOCKER_NETWORK docker network for frontend."

# start the frontend docker services
log_message "Setting up Docker for frontend branch: $FRONTEND_BRANCH..."
cd "$TEMP_DIR_PATH/tergite-frontend"
cp "$ROOT_PATH/tests/fixtures/frontend.env" .env
cp "$ROOT_PATH/tests/fixtures/mss-config.toml" mss-config.toml
docker system prune -f
docker compose -f fresh-docker-compose.yml up -d
check_error "Failed to start Docker containers for frontend."

# Check if the frontend is up on port 8002
is_frontend_live=0
for i in $(seq 1 $MAX_HTTP_RETRIES); do
  log_message "[Trial $i] Checking if the frontend is running on port 8002..."
  curl --fail http://localhost:8002 > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    sleep $HTTP_RETRY_INTERVAL
  else
    log_message "Frontend is running on port 8002."
    is_frontend_live=1
    break
  fi
done

if [ $is_frontend_live -eq 0 ]; then
    log_error "Frontend is not running on port 8002!"
    exit 1
fi

# Setup backend docker image
log_message "Setting up backend docker image; branch: $BACKEND_BRANCH..."
cd "$TEMP_DIR_PATH"
rm -rf tergite-backend
git clone --single-branch --branch "$BACKEND_BRANCH" "$BACKEND_REPO"
cd tergite-backend
docker build -t tergite-e2e/tergite-backend:latest .
check_error "Failed to build backend docker image."

# Backends setup
for i in "${!BACKENDS[@]}"; do
  cd "$TEMP_DIR_PATH"

  tuple="${BACKENDS[$i]}"
  backend=$(echo "$tuple" | cut -d ',' -f 1)
  port=$(echo "$tuple" | cut -d ',' -f 2)

  log_message "Setting up config files for $backend"
  rm -rf "$backend" 2>/dev/null
  mkdir -p "$backend/data"
  cd "$backend"
  touch data/.env
  cp "$ROOT_PATH/tests/fixtures/${backend}_backend_config.toml" data/backend_config.toml
  check_error "Failed to install backend dependencies from requirements.txt."

  # Start backend services
  log_message "Starting backend service $backend"
  docker run --name "$backend" -v ./data:/data \
    -e ENV_FILE="/data/.env" \
    -e MSS_MACHINE_ROOT_URL="http://mss:8002" \
    -e MSS_PORT=8002 \
    -e BCC_MACHINE_ROOT_URL="http://localhost:$port" \
    -e BCC_PORT=8000 \
    -e EXECUTOR_TYPE="$backend" \
    -e DEFAULT_PREFIX="$backend" \
    -e MSS_APP_TOKEN="$APP_TOKEN" \
    -e APP_SETTINGS="production" \
    -e IS_AUTH_ENABLED="True" \
    -e BACKEND_SETTINGS="/data/backend_config.toml" \
    -e REDIS_PORT=6379 \
    -e REDIS_HOST="tergite-redis" \
    --network "$DOCKER_NETWORK" \
    -p "$port":8000\
    -d \
    tergite-e2e/tergite-backend:latest

  # Check if the backend is up on port
  is_backend_live=0
  for i in $(seq 1 $MAX_HTTP_RETRIES); do
    log_message "[Trial $i] Checking if the $backend is running on port $port..."
    curl --fail "http://localhost:$port/docs" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
      sleep $HTTP_RETRY_INTERVAL
    else
      log_message "$backend is running on port $port."
      is_backend_live=1
      break
    fi
  done

  if [ $is_backend_live -eq 0 ]; then
      log_error "Backend $backend is not running on port $port!"
      exit 1
  fi
done

log_message "Create virtual environment for tests..."
cd "$ROOT_PATH"
rm -rf env
python -m venv env
. env/bin/activate
py_path=$(which python)
if [[ ! "$py_path" =~ ^"$ROOT_PATH" ]]; then
  log_error "virtual environment failed to activate; python is at $py_path"
  exit 1
fi
pip install ."[test]"
check_error "Virtual environment failed to be created."

log_message "Running end-to-end test suite..."
cd "$ROOT_PATH"
IS_END_TO_END="True" API_URL="http://127.0.0.1:8002" API_TOKEN="$APP_TOKEN" python -m pytest tests
check_error "test suite failed."
deactivate

# Cleanup backends
for i in "${!BACKENDS[@]}"; do
  tuple="${${BACKENDS[$i]}}"
  backend=$(echo "$tuple" | cut -d ',' -f 1)

  log_message "Shutting down $backend service..."
  docker rm -f "$backend" 2>/dev/null
  rm -rf "$TEMP_DIR_PATH/$backend"
  check_error "Failed to shut down $backend service."
done

# Cleanup frontend
log_message "Shutting down frontend containers..."
cd "$TEMP_DIR_PATH/tergite-frontend"
docker compose -f fresh-docker-compose.yml down --rmi all --volumes
check_error "Failed to shut down frontend Docker containers."

# Clean up everything
rm -rf "$TEMP_DIR_PATH"
check_error "Failed to remove the $TEMP_DIR_PATH folder."

docker rm -f tergite-redis
check_error "Failed to stop redis server."

docker rm -f tergite-mongo
check_error "Failed to stop mongo server."

docker network rm "$DOCKER_NETWORK" 2>/dev/null
check_error "Failed to create docker network '$DOCKER_NETWORK'."

log_message "Script completed successfully."
