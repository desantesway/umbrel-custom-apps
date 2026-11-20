# Vault Manager 1.0.6 — APP_DATA_ROOT directory picker

This version changes only the destination selection used when creating new vaults.

- The picker starts at the host path provided by `${APP_DATA_ROOT}`.
- It browses directories only, and allows selecting the current directory.
- New encrypted vaults are created in the selected directory under APP_DATA_ROOT.
- Existing vaults stored under the previous Toshiba `/vault` root remain discoverable and are not moved.
- Unlocked mountpoints remain under `/vault/Unlocked/` and use namespaced paths to avoid collisions.
- The existing FUSE/gocryptfs unlock command is retained from 1.0.5.

## Install

Replace the `custom-apps-vault-manager` folder and `.github/workflows/publish-vault-manager.yml` in your repository with the included versions. Commit and run the GitHub Actions workflow. Publish both `linux/amd64` and `linux/arm64`, tag `1.0.6`, and keep the GHCR package public.

**Important:** The host must define `APP_DATA_ROOT` for Docker Compose and it must be a directory Umbrel can bind-mount. If your Umbrel installation does not define that variable, Compose will fail until the correct host path is supplied. Existing vault data is not migrated.
