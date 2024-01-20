#!/bin/bash

# Derived from: 
# https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh

# We don't need return codes for "$(command)", only stdout is needed.
# Allow `[[ -n "$(command)" ]]`, `func "$(command)"`, pipes, etc.
# shellcheck disable=SC2312

set -u

DMON_PY_URL="https://raw.githubusercontent.com/dmon-io/client/main/dmon.py"

abort() {
  printf "%s\n" "$@" >&2
  exit 1
}

# Fail fast with a concise message when not using bash
# Single brackets are needed here for POSIX compatibility
# shellcheck disable=SC2292
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

####################################################################### script

echo "This script will install:"
echo "${INSTALL_PATH}/dmon.py"
echo "...and will add a crontab entry for: $USER"

wait_for_user

if ! command -v curl >/dev/null
then
  abort "$(
    cat <<EOABORT
You must install cURL to use this installer.
EOABORT
  )"
fi

curl -s "${DMON_PY_URL}" > /tmp/dmon.py
/usr/bin/install -D -o "${USER}" -g "${GROUP}" -m "0755" /tmp/dmon.py "${INSTALL_PATH}"

cat <<EOS
Next steps:

- Wait up to 60 seconds for a check-in
- Go to https://dmon.io/jobsconfig
- Click on the "Adoptable" tab and adopt this device, named ${DEVICENAME}

EOS
