#!/bin/bash
# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
# Runs tests/e2e against the whole stack, each service running natively, as
# tergite-frontend's dev/e2e_native_test.sh does: MongoDB, MSS from a tergite-frontend checkout,
# seeded from its ui/fixtures, and the backends from a tergite-backend checkout, all from fresh
# data in temp-native/. The simulators, each a simulated chip behind dummy Qblox clusters, run
# in one backend process, and Loke, on a dummy Qblox cluster, in another, both from one
# environment, so that each process's performance is measured apart. MSS's config and the keys
# come from the frontend's fixtures, which its own e2e keeps in step with MSS and the backend;
# the simulators' settings, chips and tuner configs from the backend's tests/fixtures, as its
# packages ship them; Loke's settings, quantify and calibration configs from this repo's
# tests/fixtures. The script's arguments go to pytest, e.g. a test to run. Needs mongod,
# mongosh, uv, git and curl.
#
# Usage
# =====
#
# FRONTEND_PATH="../tergite-frontend" \ # a tergite-frontend checkout; or else FRONTEND_REPO is cloned
#   FRONTEND_REPO="https://github.com/tergite/tergite-frontend.git" \
#   FRONTEND_BRANCH="main" \ # the branch or tag of FRONTEND_REPO to clone, else the newest
#     release of its minor one, else main
#   BACKEND_PATH="../tergite-backend" \ # a tergite-backend checkout; or else BACKEND_REPO is cloned
#   BACKEND_REPO="https://github.com/tergite/tergite-backend.git" \
#   BACKEND_BRANCH="main" \ # the branch or tag of BACKEND_REPO to clone, else the newest
#     release of its minor one, else main
#   DEBUG="True" \ # Set 'True' to keep the services running and temp-native/ after the tests, default: ''
#   PYTEST_TARGET="tests/e2e" \ # what pytest runs against the stack, default: 'tests/e2e'
#   PYTEST_WORKERS="4" \ # the pytest-xdist workers the tests under tests/e2e run in, default: '4'
#   ./dev/e2e_native_test.sh

set -e # exit if any step fails

ROOT_PATH="$(cd "$(dirname "$0")/.." && pwd)"
# the Python the stack is released with; uv would otherwise take the newest it can find
export UV_PYTHON="${UV_PYTHON:-3.13}"
WORK_PATH="$ROOT_PATH/temp-native"
SDK_FIXTURES_PATH="$ROOT_PATH/tests/fixtures"
# what pytest runs against the stack; dev/perf/record.sh runs its round trip this way
PYTEST_TARGET="${PYTEST_TARGET:-tests/e2e}"
# the e2e's tests run on three backends, so they overlap in workers; the round trip measures
# its jobs one at a time, so it runs in one
PYTEST_WORKERS="${PYTEST_WORKERS:-4}"
PYTEST_PARALLEL=()
if [[ "$PYTEST_TARGET" == tests/e2e* ]]; then
  PYTEST_PARALLEL=(-n "$PYTEST_WORKERS" --dist=worksteal)
fi
FRONTEND_BRANCH="${FRONTEND_BRANCH:-main}"
BACKEND_BRANCH="${BACKEND_BRANCH:-main}"
OPENID_CONFIG_URL="${OPENID_CONFIG_URL:-https://samples.auth0.com/.well-known/openid-configuration}"
OPENID_CLIENT_ID="${OPENID_CLIENT_ID:-kbyuFDidLLm280LIwVFiazOqjO3ty8KH}"
OPENID_CLIENT_SECRET="${OPENID_CLIENT_SECRET:-60Op4HFM0I8ajz0WdiStAbziZ-VFQttXuxixHHs2R7r7-CW8GR79l-mmLqMhc-Sa}"
# ports of their own, so that this runs beside tergite-frontend's e2e
MSS_PORT=8202
MONGO_PORT=27218
SIMULATORS_PORT=8201
LOKE_PORT=8203
# the app token of an active project with QPU seconds in the frontend's ui/fixtures/tokens.json
APP_TOKEN="pZTccp8F-8RLFvQie1AMM0ptfdkGNnH1wDEB4INUFqw"
LOKE_JWT_SECRET="e9fae9efa7c3ff10348acde323baa5273db8021712ecb1f59fdf0e8336240fb7d70c6d8d"
PIDS=()

# Logging function for errors
log_error() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - ERROR: $1" >&2
}

# exits the program with an error
# usage:
#   exit_with_err "some string"
exit_with_err() {
  log_error "$1";
  exit 1;
}

for tool in mongod mongosh uv git curl; do
  command -v "$tool" &> /dev/null || exit_with_err "$tool is not available"
done

# replaces the given string in a given file with another string
# usage:
#   replace_str file "original string" "new string"
replace_str() {
  if [[ "$(uname -s)" = "Darwin" ]]; then
    sed -i "" "s|$2|$3|" "$1";
  else
    sed -i "s|$2|$3|" "$1";
  fi
}

# starts a command in the background, logging to temp-native/logs/<name>.log, and sets
# SERVICE_PID to its process ID
# usage:
#   start_service name command [args...]
start_service() {
  local name=$1;
  shift;
  "$@" > "$WORK_PATH/logs/$name.log" 2>&1 &
  SERVICE_PID=$!;
  PIDS+=($SERVICE_PID);
}

# waits until the URL answers 200, failing if the service's process exits or it takes longer
# than the given seconds
# usage:
#   wait_for_url name url pid seconds
wait_for_url() {
  local deadline=$(( $(date +%s) + $4 ));
  until [[ "$(curl -s -o /dev/null -w '%{http_code}' "$2")" = "200" ]]; do
    kill -0 "$3" 2>/dev/null || exit_with_log "$1" "$1 stopped";
    [[ $(date +%s) -lt $deadline ]] || exit_with_log "$1" "$2 did not answer within $4 seconds";
    sleep 0.5;
  done
}

# exits with the error after the end of the service's log in temp-native/logs/, as a CI job
# shows its output and keeps the logs only as an artifact
# usage:
#   exit_with_log name "some string"
exit_with_log() {
  echo "The end of temp-native/logs/$1.log:"
  tail -n 50 "$WORK_PATH/logs/$1.log" 2>/dev/null || true
  exit_with_err "$2";
}

# stops the services, and removes temp-native/ but its environments and logs, unless DEBUG is set
# usage:
#   stop_stack
stop_stack() {
  if [[ $(echo "${DEBUG}" | tr '[:lower:]' '[:upper:]') = "TRUE" ]]; then
    echo "Not stopping the services, $(IFS=' '; echo "${PIDS[*]}"), because DEBUG=$DEBUG";
    return;
  fi
  echo "Stopping the services"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true;
  done
  wait 2>/dev/null || true;
  find "$WORK_PATH" -mindepth 1 -maxdepth 1 ! -name venvs ! -name logs ! -name repos -exec rm -rf {} +;
}

# prints the repository's newest release of the minor release the given tag is of, e.g.
# v2026.11.3 for v2026.11.1, as every release of a minor one works with the others; a final
# release before any candidate, and nothing for a ref of no minor release
# usage:
#   get_minor_tag repo tag
get_minor_tag() {
  local tags;
  [[ "$2" =~ ^(v[0-9]{4}\.[0-9]{2})\. ]] || return 0;
  tags="$(git ls-remote --tags --refs -q "$1" "refs/tags/${BASH_REMATCH[1]}.*" | sed 's|.*refs/tags/||')";
  { grep -v -- "-rc" <<< "$tags" | sort -V | tail -n 1 | grep .; } \
    || { grep -- "-rc" <<< "$tags" | sort -V | tail -n 1; } || true;
}

# sets CHECKOUT_PATH to the given checkout, or else to a clone of the repository's branch, or
# of the newest release of its minor release, or of main where it has neither
# usage:
#   get_checkout name path repo branch
get_checkout() {
  if [[ -n "$2" ]]; then
    CHECKOUT_PATH="$(cd "$2" && pwd)";
    return;
  fi
  [[ -n "$3" ]] || exit_with_err "set the path or the repository of $1";
  local branch="$4" minor_tag;
  if ! git ls-remote --exit-code -q "$3" "refs/heads/$branch" "refs/tags/$branch" > /dev/null; then
    minor_tag="$(get_minor_tag "$3" "$branch")";
    echo "$1 has no branch or tag $branch; cloning ${minor_tag:-main}";
    branch="${minor_tag:-main}";
  fi
  echo "Cloning $1's $branch..."
  rm -rf "$WORK_PATH/repos/$1";
  git clone -q --single-branch --branch "$branch" "$3" "$WORK_PATH/repos/$1";
  CHECKOUT_PATH="$WORK_PATH/repos/$1";
}

# writes the env file of a backend's device, from its line of SIMULATORS or LOKE, with the
# given settings of its instruments and tuner after its own
# usage:
#   write_env_file "name|port|jwt secret|backend config|calibration seed" "BCC_<NAME>=value"...
write_env_file() {
  local name port jwt_secret settings seed stem dir;
  IFS="|" read -r name port jwt_secret settings seed <<< "$1";
  shift;
  stem="$(echo "$name" | tr '[:upper:]' '[:lower:]')";
  dir="$WORK_PATH/backends/$name";
  mkdir -p "$dir/storage";
  # a copy, as a recalibration writes what it found over its seed
  cp "$seed" "$dir/calibration.seed.toml";
  {
    echo "BCC_DEFAULT_PREFIX=$name"
    echo "BCC_APP_SETTINGS=production"
    echo "BCC_JWT_SECRET=$jwt_secret"
    echo "BCC_CORS_ORIGINS=127.0.0.1,localhost"
    echo "BCC_MACHINE_ROOT_URL=http://127.0.0.1:$port/$name"
    echo "BCC_MSS_MACHINE_ROOT_URL=http://127.0.0.1:$MSS_PORT"
    # it starts before MSS, so it tries MSS each second until MSS answers, not after
    # waits that double to a minute
    echo "BCC_MSS_MAX_RECONNECTION_DELAY=1"
    echo "BCC_MSS_CONNECTION_MAX_ATTEMPTS=120"
    echo "BCC_STORAGE_ROOT=$dir/storage"
    echo "BCC_BOOKING_DB_URL=sqlite:///$dir/booking_db.db"
    echo "BCC_BACKEND_SETTINGS=$settings"
    echo "BCC_CALIBRATION_SEED=$dir/calibration.seed.toml"
    echo "BCC_PRIVATE_KEY_FILE=$FIXTURES_PATH/private-$(echo "$stem" | tr '_' '-')-key.pem"
    echo "BCC_MSS_PUBLIC_KEY_PATH=$FIXTURES_PATH/public-mss-key.pem"
    printf '%s\n' "$@"
  } > "$dir/backend.env";
}

for port in $MSS_PORT $MONGO_PORT $SIMULATORS_PORT $LOKE_PORT; do
  ! (exec 3<> "/dev/tcp/127.0.0.1/$port") 2> /dev/null || exit_with_err "port $port is in use"
done

trap stop_stack EXIT

echo "Creating $WORK_PATH"
find "$WORK_PATH" -mindepth 1 -maxdepth 1 ! -name venvs ! -name repos -exec rm -rf {} + 2>/dev/null || true
mkdir -p "$WORK_PATH/logs" "$WORK_PATH/mongo" "$WORK_PATH/venvs" "$WORK_PATH/repos"

get_checkout tergite-frontend "$FRONTEND_PATH" "$FRONTEND_REPO" "$FRONTEND_BRANCH"
FRONTEND_PATH="$CHECKOUT_PATH"
FIXTURES_PATH="$FRONTEND_PATH/ui/fixtures"
get_checkout tergite-backend "$BACKEND_PATH" "$BACKEND_REPO" "$BACKEND_BRANCH"
BACKEND_PATH="$CHECKOUT_PATH"
BACKEND_FIXTURES_PATH="$BACKEND_PATH/tests/fixtures"
# name|port|JWT secret|backend config|calibration seed
SIMULATORS=(
  "sim_1q|$SIMULATORS_PORT|dd94de9017e976973769aaf5d426fdb95cab46feda584dbdbc5f3f02bbf8ae8ce77211d7|$BACKEND_FIXTURES_PATH/backend_config.simq1.toml|$BACKEND_FIXTURES_PATH/sim_1q.seed.toml"
  "sim_2q|$SIMULATORS_PORT|$LOKE_JWT_SECRET|$BACKEND_FIXTURES_PATH/backend_config.simq2.toml|$BACKEND_FIXTURES_PATH/sim_2q.seed.toml"
)
# their chip behind the dummy clusters, which the tuner recalibrates from its device config
SIMULATOR_CONFIGS=(
  "BCC_QUANTIFY_CONFIG_FILE=$BACKEND_FIXTURES_PATH/dummy-quantify-config.json"
  "BCC_QUANTIFY_METADATA_FILE=$BACKEND_FIXTURES_PATH/dummy-quantify-metadata.yml"
  "BCC_CALIBRATION_NODE_CONFIG_FILE=$BACKEND_FIXTURES_PATH/chip_node_config.toml"
  "BCC_CALIBRATION_DEVICE_CONFIG_FILE=$BACKEND_FIXTURES_PATH/chip_calib_device_config.toml"
  "BCC_CALIBRATION_SPI_CONFIG_FILE=$BACKEND_FIXTURES_PATH/dummy_spi_config.calib.toml"
)
# the frontend's Loke has 8 qubits and is never recalibrated, as its e2e runs no worker; this
# one is the dummy 2-qubit Loke that this repo's calibration configs recalibrate
LOKE="Loke|$LOKE_PORT|$LOKE_JWT_SECRET|$SDK_FIXTURES_PATH/loke.toml|$SDK_FIXTURES_PATH/loke.seed.toml"
LOKE_CONFIGS=(
  "BCC_QUANTIFY_CONFIG_FILE=$SDK_FIXTURES_PATH/quantify-config.json"
  "BCC_QUANTIFY_METADATA_FILE=$SDK_FIXTURES_PATH/quantify-metadata.yml"
  "BCC_CALIBRATION_NODE_CONFIG_FILE=$SDK_FIXTURES_PATH/node_config.calib.toml"
  "BCC_CALIBRATION_DEVICE_CONFIG_FILE=$SDK_FIXTURES_PATH/device_config.calib.toml"
  "BCC_CALIBRATION_SPI_CONFIG_FILE=$SDK_FIXTURES_PATH/spi_config.calib.toml"
)

# environments of their own, so that each checkout's .venv stays as it is
echo "Installing MSS, the backends and the SDK"
UV_PROJECT_ENVIRONMENT="$WORK_PATH/venvs/mss" uv sync -q --frozen --no-dev --project "$FRONTEND_PATH"
UV_PROJECT_ENVIRONMENT="$WORK_PATH/venvs/backend" uv sync -q --frozen --no-dev --project "$BACKEND_PATH"
UV_PROJECT_ENVIRONMENT="$WORK_PATH/venvs/sdk" uv sync -q --frozen --project "$ROOT_PATH"

echo "Starting MongoDB"
start_service mongod mongod --dbpath "$WORK_PATH/mongo" --port $MONGO_PORT --bind_ip 127.0.0.1
# a TCP connection, as each mongosh it would take to ping costs a second
until (exec 3<>"/dev/tcp/127.0.0.1/$MONGO_PORT") 2>/dev/null; do sleep 0.2; done

# the backends take longest to start, so they start while MSS is seeded and starts; each
# keeps what it sends MSS until MSS answers
echo "Starting the backends"
simulator_env_args=()
for backend in "${SIMULATORS[@]}"; do
  write_env_file "$backend" "${SIMULATOR_CONFIGS[@]}"
  IFS="|" read -r name _ <<< "$backend"
  simulator_env_args+=(--env-file "$WORK_PATH/backends/$name/backend.env")
done
write_env_file "$LOKE" "${LOKE_CONFIGS[@]}"
start_service simulators bash -c "cd '$WORK_PATH/backends' && exec '$WORK_PATH/venvs/backend/bin/python' '$BACKEND_PATH/main.py' start --host 127.0.0.1 --port $SIMULATORS_PORT ${simulator_env_args[*]}"
simulators_pid=$SERVICE_PID
start_service loke bash -c "cd '$WORK_PATH/backends' && exec '$WORK_PATH/venvs/backend/bin/python' '$BACKEND_PATH/main.py' start --host 127.0.0.1 --port $LOKE_PORT --env-file '$WORK_PATH/backends/Loke/backend.env'"
loke_pid=$SERVICE_PID

echo "Starting MSS"
cp "$FIXTURES_PATH/mss-config.toml" "$WORK_PATH/mss-config.toml"
replace_str "$WORK_PATH/mss-config.toml" "mongodb://tergite-mongo:27017" "mongodb://127.0.0.1:$MONGO_PORT"
replace_str "$WORK_PATH/mss-config.toml" "bcc_certs/" "$FIXTURES_PATH/"
replace_str "$WORK_PATH/mss-config.toml" "OPENID_CLIENT_ID" "$OPENID_CLIENT_ID"
replace_str "$WORK_PATH/mss-config.toml" "OPENID_CLIENT_SECRET" "$OPENID_CLIENT_SECRET"
replace_str "$WORK_PATH/mss-config.toml" "OPENID_CONFIG_URL" "$OPENID_CONFIG_URL"
for backend in "${SIMULATORS[@]}" "$LOKE"; do
  IFS="|" read -r name port _ <<< "$backend"
  host="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
  replace_str "$WORK_PATH/mss-config.toml" "http://$host:8000" "http://127.0.0.1:$port/$name"
done
export MSS_CONFIG_FILE="$WORK_PATH/mss-config.toml" PRIVATE_KEY_FILE="$FIXTURES_PATH/private-mss-key.pem"
(cd "$FRONTEND_PATH" && "$WORK_PATH/venvs/mss/bin/python" -m dev.seed) > "$WORK_PATH/logs/seed.log" 2>&1 \
  || exit_with_log seed "seeding MSS's database failed"
# the dashboard's fixtures show Loke switched off, which this e2e runs jobs on
mongosh --quiet "mongodb://127.0.0.1:$MONGO_PORT/testing" --eval 'db.switched_off_devices.deleteMany({name: "Loke"})' > /dev/null
start_service mss bash -c "cd '$FRONTEND_PATH' && exec '$WORK_PATH/venvs/mss/bin/python' main.py start --host 127.0.0.1 --port $MSS_PORT"
mss_pid=$SERVICE_PID
unset MSS_CONFIG_FILE PRIVATE_KEY_FILE
wait_for_url mss "http://127.0.0.1:$MSS_PORT/health" $mss_pid 60
wait_for_url simulators "http://127.0.0.1:$SIMULATORS_PORT/health" $simulators_pid 300
wait_for_url loke "http://127.0.0.1:$LOKE_PORT/health" $loke_pid 300
# the fixtures seed no simulator, so each is in MSS once its backend has sent it
for backend in "${SIMULATORS[@]}"; do
  IFS="|" read -r name _ <<< "$backend"
  wait_for_url simulators "http://127.0.0.1:$MSS_PORT/calibrations/$name" $simulators_pid 300
done

echo "Checking that MSS and the backend serve the schemas dev/openapi pins"
"$WORK_PATH/venvs/sdk/bin/python" -m dev.openapi.check_served "http://127.0.0.1:$MSS_PORT/openapi.json" mss.json \
  || exit_with_err "MSS's API is not the one the SDK's models were generated from"
"$WORK_PATH/venvs/sdk/bin/python" -m dev.openapi.check_served "http://127.0.0.1:$SIMULATORS_PORT/openapi.json" bcc.json \
  || exit_with_err "the backend's API is not the one the SDK's models were generated from"

echo "Running $PYTEST_TARGET..."
cd "$ROOT_PATH"
IS_END_TO_END="True" \
  API_URL="http://127.0.0.1:$MSS_PORT" \
  API_TOKEN="$APP_TOKEN" \
  MSS_PID=$mss_pid SIMULATORS_PID=$simulators_pid LOKE_PID=$loke_pid \
  "$WORK_PATH/venvs/sdk/bin/python" -m pytest "$PYTEST_TARGET" "${PYTEST_PARALLEL[@]}" "$@"

echo "Script completed."
