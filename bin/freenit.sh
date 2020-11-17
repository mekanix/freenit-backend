#!/bin/sh

set -e


if [ "${1}" = "--version" ]; then
  echo "0.1.16"
  exit 0
fi


NAME="${1}"
TYPE="${2}"
if [ -z "${NAME}" -o -z "${TYPE}" ]; then
  echo "Usage: $0 <project name> <project type>" >&2
  exit 1
fi


PROJECT_ROOT=`python${PY_VERSION} -c 'import os; import freenit; print(os.path.dirname(os.path.abspath(freenit.__file__)))'`
SED_CMD="sed -i"


mkdir ${NAME}
cd ${NAME}
echo "freenit[${TYPE}]" >requirements.txt
cp -r ${PROJECT_ROOT}/project/* .

case `uname` in
  *BSD)
    ${SED_CMD} '' -e "s/TYPE/${TYPE}/g" project/models/role.py
    ${SED_CMD} '' -e "s/TYPE/${TYPE}/g" project/models/user.py
    ;;
  *)
    ${SED_CMD} -e "s/TYPE/${TYPE}/g" project/models/role.py
    ${SED_CMD} -e "s/TYPE/${TYPE}/g" project/models/user.py
    ;;
esac
mv project ${NAME}
echo "app_name=\"${NAME}\"  # noqa: E225" >name.py
echo "ipdb" >requirements_dev.txt
echo "DEVEL_MODE = YES" >vars.mk
cat > Makefile << EOF
.include <name.py>

USE_FREENIT = YES
SERVICE != echo \${app_name}
REGGAE_PATH := /usr/local/share/reggae
SYSPKG := YES

.include <\${REGGAE_PATH}/mk/service.mk>
EOF

cat >.gitignore <<EOF
.coverage
.provisioned
.pytest_cache
__pycache__

ansible/group_vars/all
ansible/inventory/inventory
ansible/roles/*
ansible/site.yml
!ansible/roles/.keep
!ansible/roles/devel

build
cbsd.conf
coverage.xml
database.db
fstab
local_config.py
project.mk
site.retry
test.db
vars.mk

dist/
*.egg-info/
EOF

mkdir templates
echo "- onelove-roles.freebsd_freenit" >>requirements.yml
if [ "${TYPE}" = "sql" ]; then
  echo "- onelove-roles.freebsd_freenit_sql" >>requirements.yml
  echo "    - onelove-roles.freebsd_freenit_sql" >>templates/site.yml.tpl
elif [ "${TYPE}" = "mongo" ]; then
  echo "- onelove-roles.freebsd_freenit_mongoengine" >>requirements.yml
  echo "    - onelove-roles.freebsd_freenit_mongoengine" >>templates/site.yml.tpl
elif [ "${TYPE}" = "all" ]; then
  echo "- onelove-roles.freebsd_freenit_sql" >>requirements.yml
  echo "- onelove-roles.freebsd_freenit_mongoengine" >>requirements.yml
  echo "    - onelove-roles.freebsd_freenit_sql" >>templates/site.yml.tpl
  echo "    - onelove-roles.freebsd_freenit_mongoengine" >>templates/site.yml.tpl
fi
