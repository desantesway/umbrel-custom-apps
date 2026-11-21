# Vault Manager 1.1.0 — dashboard scan performance fix

Fixes the main dashboard taking a long time to load.

The previous dashboard recursively searched the entire APP_DATA_ROOT and legacy vault root using `Path.rglob()`. Because APP_DATA_ROOT can contain a large external drive and FUSE mountpoints, this could block the home page.

The new scanner:
- Uses bounded directory traversal (maximum six levels).
- Does not follow symlinks.
- Skips `Unlocked`, app state directories, and hidden directories.
- Stops descending once it finds a gocryptfs vault.
- Handles disconnected FUSE mount errors without failing the dashboard.

The existing vault storage and unlocked-location picker behavior from 1.0.9 is retained. No encrypted vault data is moved or deleted.

## Publish/update

1. Replace `custom-apps-vault-manager/` in your GitHub repository with this folder.
2. Replace `.github/workflows/publish-vault-manager.yml` with the included workflow.
3. Commit and run the GitHub Actions workflow.
4. Ensure GHCR package visibility is Public.
5. Update Vault Manager in Umbrel.

Image tags: `1.1.0` and `latest`, built for `linux/amd64` and `linux/arm64`.

The scanner searches up to six directory levels below each configured root. If you store encrypted vaults deeper than that, they will not appear in the dashboard until the scan depth is adjusted.
