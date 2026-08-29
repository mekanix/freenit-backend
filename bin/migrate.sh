#!/bin/sh

BIN_DIR=`dirname $0`
export FREENIT_ENV=${FREENIT_ENV:="development"}
export OFFLINE=${OFFLINE:="yes"}

. "${BIN_DIR}/common.sh"
setup no yes
