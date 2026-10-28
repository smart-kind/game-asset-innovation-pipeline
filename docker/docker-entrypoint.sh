#!/bin/bash
set -e -o pipefail

### Container entrypoint
# Runs the CMD as defined in the Dockerfile or passed to `docker run`
# Can be used to configure the runtime dir
# Bypass by using ENTRYPOINT or `--entrypoint`

### Set INVOKEAI_ROOT pointing to a valid runtime directory
# Otherwise configure the runtime dir first.

### Set the CONTAINER_UID envvar to match your user.
# Ensures files created in the container are owned by you:
#   docker run --rm -it -v /some/path:/invokeai -e CONTAINER_UID=$(id -u) <this image>
# Default UID: 1000 chosen due to popularity on Linux systems. Possibly 501 on MacOS.

USER_ID=${CONTAINER_UID:-1000}
USER=ubuntu
# if the user does not exist, create it. It is expected to be present in ubuntu >=24.x
_=$(id ${USER} 2>&1) || useradd -u ${USER_ID} ${USER}
# ensure the UID is correct
usermod -u ${USER_ID} ${USER} 1>/dev/null

mkdir -p "${INVOKEAI_ROOT}"
chown --recursive ${USER} "${INVOKEAI_ROOT}" || true
cd "${INVOKEAI_ROOT}"

# Run the CMD as the Container User (not root).
exec gosu ${USER} "$@"
