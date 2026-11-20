# Vault Manager — Umbrel custom app

This app folder follows the naming and layout used by the other apps in this
custom app store: `custom-apps-vault-manager/`.

## Image prerequisite

The Compose file expects `ghcr.io/desantesway/vault-manager:1.0.0`.
Build this folder's Dockerfile and publish that image to GitHub Container
Registry before installing the app. Uploading this source folder to the app
store does not build or publish the container image.

## External drive

The app expects the Toshiba drive's Vault folder at:

`/home/umbrel/umbrel/external/TOSHIBA HDW/Vault`

Unlocked FUSE mounts are created under its `Unlocked/` subfolder.

The container requires `/dev/fuse`, `SYS_ADMIN`, `apparmor:unconfined`, and
shared mount propagation. This is elevated access. Keep the app private and
do not expose it directly to the public internet. Test with disposable data
first, and keep recovery keys somewhere separate from the external drive.
Lock vaults before stopping the app or unplugging the disk.

The web UI uses the Umbrel app password (`APP_PASSWORD`). Each vault has its
own password, which the app does not persist.
