#!/bin/sh
set -eu
VAULT_PATH="/home/umbrel/umbrel/external/TOSHIBA HDW/Vault"

if [ ! -d "$VAULT_PATH" ]; then
  echo "Vault path does not exist: $VAULT_PATH" >&2
  exit 1
fi

TARGET="$(findmnt -n -o TARGET -T "$VAULT_PATH")"
SOURCE="$(findmnt -n -o SOURCE -T "$VAULT_PATH")"

echo "Filesystem source: $SOURCE"
echo "Mounted at:        $TARGET"
echo
echo "Verify that the source above is your Toshiba external drive."
case "$TARGET" in
  "/"|"/home"|"/home/umbrel")
    echo "Refusing to mark a broad system mount shared. Is the Toshiba drive mounted?" >&2
    exit 1
    ;;
esac

mount --make-rshared "$TARGET"
echo "Mount propagation set to rshared for $TARGET"
