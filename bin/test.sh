#!/bin/sh

set -eu

BIN_DIR=`dirname $0`
export FREENIT_ENV="testing"
export OFFLINE=${OFFLINE:="no"}

. "${BIN_DIR}/common.sh"
setup yes no

pytest -v "$@"
