#!/bin/sh

set -eu

export BIN_DIR=`dirname $0`
export PROJECT_ROOT="${BIN_DIR}/.."
. "${PROJECT_ROOT}/name.py"
export VIRTUALENV=${VIRTUALENV:="${app_name}"}
export FREENIT_ENV=${FREENIT_ENV:="production"}
export PIP_INSTALL="pip install -U --upgrade-strategy eager"
export OFFLINE=${OFFLINE:="no"}

setup() {
  cd "${PROJECT_ROOT}"
  run_migrations="${2:-yes}"
  if [ ! -d "${HOME}/.virtualenvs/${VIRTUALENV}" ]; then
    python${PY_VERSION:-3} -m venv "${HOME}/.virtualenvs/${VIRTUALENV}"
  fi
  . "${HOME}/.virtualenvs/${VIRTUALENV}/bin/activate"

  if [ "${1:-yes}" != "no" ] && [ "${OFFLINE}" != "yes" ]; then
    ${PIP_INSTALL} pip wheel
    ${PIP_INSTALL} -e ".[dev]"
  fi

  if [ "${run_migrations}" != "no" ]; then
    oxyde migrate
  fi
}
