#!/bin/sh


export BIN_DIR=`dirname $0`
export PROJECT_ROOT="${BIN_DIR}/.."
. "${PROJECT_ROOT}/name.py"
export VIRTUALENV=${VIRTUALENV:="${app_name}"}
export FREENIT_ENV=${FREENIT_ENV:="prod"}
export SYSPKG=${SYSPKG:="no"}
export SYSPKG=`echo ${SYSPKG} | tr '[:lower:]' '[:upper:]'`
export DB_TYPE=${DB_TYPE:="ormar"}
export PIP_INSTALL="pip install -U --upgrade-strategy eager"


setup() {
  cd ${PROJECT_ROOT}
  if [ "${SYSPKG}" != "YES" ]; then
    update=${1}
    if [ ! -d ${HOME}/.virtualenvs/${VIRTUALENV} ]; then
        python${PY_VERSION} -m venv "${HOME}/.virtualenvs/${VIRTUALENV}"
    fi
    . ${HOME}/.virtualenvs/${VIRTUALENV}/bin/activate

    INSTALL_TARGET=".[${DB_TYPE}"
    if [ "${FREENIT_ENV}" != "prod" ]; then
      INSTALL_TARGET="${INSTALL_TARGET},${FREENIT_ENV}"
    fi
    INSTALL_TARGET="${INSTALL_TARGET}]"
    if [ "${update}" != "no" ]; then
      ${PIP_INSTALL} pip wheel
      ${PIP_INSTALL} -e "${INSTALL_TARGET}"
    fi
  fi

  if [ "${DB_TYPE}" = "ormar" ]; then
    if [ ! -e "alembic/versions" ]; then
      mkdir alembic/versions
      alembic revision --autogenerate -m initial
    fi
    alembic upgrade head
  fi
}
