#!/usr/bin/env bash

cd "$(dirname "$0")/.." || exit

pytest --cov=pingou "${@}" tests/*.py
