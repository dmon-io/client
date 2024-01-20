#!/bin/bash

# Derived from: 
# https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh

# We don't need return codes for "$(command)", only stdout is needed.
# Allow `[[ -n "$(command)" ]]`, `func "$(command)"`, pipes, etc.
# shellcheck disable=SC2312

set -u
set -e

DMON_PY_URL="https://raw.githubusercontent.com/dmon-io/client/main/dmon.py"

abort() {
  printf "%s\n" "$@" >&2
  exit 1
}

# must be bash
if [ -z "${BASH_VERSION:-}" ]
then
  abort "Bash is required to interpret this script."
fi

# Check if script is run in POSIX mode
if [[ -n "${POSIXLY_CORRECT+1}" ]]
then
  abort 'Bash must not run in POSIX mode. Please unset POSIXLY_CORRECT and try again.'
fi

# USER isn't always set so provide a fall back for the installer and subprocesses.
if [[ -z "${USER-}" ]]
then
  USER="$(chomp "$(id -un)")"
  export USER
fi

# Linux only
OS="$(uname)"
if [[ "${OS}" != "Linux" ]]
then
  abort "dmon.io client installer is only supported on Linux."
fi

# check running as root
if  [[ "${EUID:-${UID}}" == "0" ]]
then
  GROUP="admin"
  INSTALL_PATH="/usr/local/bin"
else
  GROUP="$(chomp "$(id -g)")"
  INSTALL_PATH="~/.local/bin"
fi

#################### telemetryKey and jobName

check_telemetry_key() {
  if [[ ${TELEMETRY_KEY} =~ ^[a-zA-Z0-9]{22}$ ]]
  then
    return
  else
    abort "telemetryKey is invalid. Please verify a correct key from dmon.io."
  fi
}

check_job_name() {
  if [[ ${JOB_NAME} =~ ^[-a-zA-Z0-9()$_=/,.\ ]{1,24}$ ]]
  then
    return
  else
    abort "jobName is invalid. Must be 1-24 characters of [-a-zA-Z0-9()\$_=/,. ]"
  fi
}

if [[ -z "${TELEMETRY_KEY-}" ]]
then
  echo ""
  echo "Please enter telemetryKey as issued on dmon.io/jobs/config"
  read -p 'telemetryKey: ' TELEMETRY_KEY
fi
check_telemetry_key

if [[ -z "${JOB_NAME-}" ]]
then
  echo ""
  echo "Please enter a device name. It must be unique for your dmon.io account"
  echo "and must be 1-24 characters in [-a-zA-Z0-9()\$_=/,. ]"
  read -p 'jobName: ' JOB_NAME
fi
check_job_name

#################### prompt before actually doing anything

getc() {
  local save_state
  save_state="$(/bin/stty -g)"
  /bin/stty raw -echo
  IFS='' read -r -n 1 -d '' "$@"
  /bin/stty "${save_state}"
}

wait_for_user() {
  local c
  echo
  echo "Press RETURN/ENTER to continue or any other key to abort:"
  getc c
  # we test for \r and \n because some stuff does \r instead
  if ! [[ "${c}" == $'\r' || "${c}" == $'\n' ]]
  then
    exit 1
  fi
}

##########################################################################
#################### actual script

echo ""
echo "This script will install:"
echo "${INSTALL_PATH}/dmon.py"
if [[ ${USER} == "root" ]]
then
  echo "/etc/cron.d/dmon"
else
  echo "...and will add a crontab entry for: $USER"
fi

wait_for_user

if ! command -v curl >/dev/null
then
  abort "$(
    cat <<EOABORT

You must install cURL to use this installer.
EOABORT
  )"
fi

################### install dmon.py

curl -s "${DMON_PY_URL}" > /tmp/dmon.py
/usr/bin/install -D -o "${USER}" -g "${GROUP}" -m "0755" /tmp/dmon.py "${INSTALL_PATH}"


################### install crontab

if [[ ${USER} == "root" ]]
then
  # is ok to just overwrite this
  echo "* * * * * daemon ${INSTALL_PATH}/dmon.py --cron ${TELEMETRY_KEY} \"${JOB_NAME}\"" > /etc/cron.d/dmon
else
  # remove any previous dmon.py entry first, so this automated script only
  # works for one entry for a user
  ( (crontab -l | grep -v "/dmon.py "); echo "* * * * * ${INSTALL_PATH}/dmon.py --cron ${TELEMETRY_KEY} \"${JOB_NAME}\"" ) | crontab -
fi

cat <<EOS

COMPLETE!
Next steps:

- Wait up to 60 seconds for a check-in
- Go to https://dmon.io/jobsconfig
- Click on the "Adoptable" tab and adopt this device, named "${JOB_NAME}"

EOS
