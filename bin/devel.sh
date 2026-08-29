#!/bin/sh

BIN_DIR=`dirname $0`
export FREENIT_ENV="development"
export OFFLINE=${OFFLINE:="no"}

. "${BIN_DIR}/common.sh"
setup yes yes

flask --app freenit run --debug
