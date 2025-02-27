#!/bin/bash
# This is a small script that is used to run the e2e tests after
# the dependent services are set up

set -e  # Exit on error

# Install some dependencies necessary for numpy on python 3.13
if  [[ $(python --version) == 'Python 3.13'* ]]; then
  apt update;
  apt install -y libopenblas-dev gfortran;
fi

pip install ."[test]"
IS_END_TO_END="True" \
  API_URL="$API_URL" \
  API_TOKEN="$APP_TOKEN" \
  IS_IN_DOCKER="True" \
  pytest tests