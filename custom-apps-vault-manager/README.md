# Vault Manager 1.0.7 — correct Umbrel app-data directory mapping

This release corrects the storage-directory picker.

Umbrel supplies `${APP_DATA_DIR}` as a host-side path for this app's persistent data directory. Docker now mounts that directory into the container at `/app-data`:

    ${APP_DATA_DIR}:/app-data

The picker starts at `/app-data`, which is the real mounted directory. It no longer tries to bind a separate `${APP_DATA_ROOT}` host variable.

The app's internal persistent state remains in `/app-data/data`, which maps to the same host-side `${APP_DATA_DIR}/data` location used by the previous release. Existing session state is therefore preserved.

## Publish

1. Replace `custom-apps-vault-manager/` in the repository with this folder.
2. Replace `.github/workflows/publish-vault-manager.yml` with the included workflow.
3. Commit and run the GitHub Actions workflow.
4. Confirm the GHCR package is Public.
5. Update the app from the Umbrel custom app store.

The image tags are `1.0.7` and `latest`, built for `linux/amd64` and `linux/arm64`.

Existing vaults on the Toshiba drive are not moved. The picker only selects the directory in which a new encrypted vault is created.
