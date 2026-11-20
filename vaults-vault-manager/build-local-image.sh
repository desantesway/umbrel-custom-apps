#!/bin/sh
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
docker build -t vault-manager:1.0.0 "$HERE"
