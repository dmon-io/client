#!/bin/bash

# Derived from: 
# https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh

set -u
set -e

DMON_PY_URL="https://raw.githubusercontent.com/dmon-io/client/main/dmon.py"

abort() {
  printf "%s\n" "$@" >&2
  exit 1
}

chomp() {
  printf "%s" "${1/"$'\n'"/}"
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
  GROUP="daemon"
  INSTALL_PATH="/usr/local/bin"
else
  GROUP="$(chomp "$(id -g)")"
  INSTALL_PATH="${HOME}/.local/bin"
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

################### try to figure out default net device

NET=$(ip -oneline link show up | cut -d ' ' -f 2 | cut -d ':' -f 1 | grep -v -E "^(veth|br-|dock|lo)" | head -n 1)

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

TMPFILE=$(mktemp -t dmon-XXXXXX)
curl -sSf "${DMON_PY_URL}" > "${TMPFILE}"
/usr/bin/install -D -o "${USER}" -g "${GROUP}" -m "0755" "${TMPFILE}" "${INSTALL_PATH}/dmon.py"
rm -f "${TMPFILE}"


################### install crontab

if [[ ${USER} == "root" ]]
then
  # is ok to just overwrite this
  NEWCRON="* * * * * daemon ${INSTALL_PATH}/dmon.py --net ${NET} --cron ${TELEMETRY_KEY} \"${JOB_NAME}\""
  echo "${NEWCRON}" > /etc/cron.d/dmon
else
  # remove any previous dmon.py entry first, so this automated script only
  # works for one entry for a user
  NEWCRON="* * * * * ${INSTALL_PATH}/dmon.py --net ${NET} --cron ${TELEMETRY_KEY} \"${JOB_NAME}\""
  OLDCRON=$( crontab -l | grep -v "/dmon.py " || true )
  (echo "${OLDCRON}"; echo "${NEWCRON}") | crontab -
fi

cat <<EOS

COMPLETE!
Next steps:

- Wait up to 60 seconds for a check-in
- Go to https://dmon.io/jobsconfig
- Click on the "Adoptable" tab and adopt this device, named "${JOB_NAME}"

EOS
