# Vault Manager — Umbrel custom app

Upload the `vault-manager/` directory to the root of `desantesway/umbrel-custom-apps`.

## Important image prerequisite

The Compose file expects this image:
`ghcr.io/desantesway/vault-manager:1.0.0`

That image must be built and pushed to GitHub Container Registry before installing from Umbrel. A source ZIP upload alone does not publish the image. Build from this directory and publish the image using Docker Buildx / GHCR, then ensure the package path matches the actual image name and tag.

## External drive

The app expects the Toshiba drive mounted at:
`/home/umbrel/umbrel/external/TOSHIBA HDW/Vault`

Unlocked FUSE mounts are created under:
`/home/umbrel/umbrel/external/TOSHIBA HDW/Vault/Unlocked`

Before first use, verify the drive mount and shared propagation on the host. The container requires `/dev/fuse`, `SYS_ADMIN`, and `apparmor:unconfined`; this is elevated access. Do not expose the app directly to the public internet.

Test with disposable data first. Keep gocryptfs recovery keys securely backed up outside the external drive. Lock vaults before stopping the app or unplugging the disk.

The app uses Umbrel's `APP_PASSWORD` for its web UI. Vault passwords are individually supplied at unlock and are not persisted by the app.
