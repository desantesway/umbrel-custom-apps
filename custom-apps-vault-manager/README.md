# Vault Manager 1.0.9 — choose unlocked mount location

This update adds a second directory picker during vault creation.

- The encrypted vault picker chooses where the gocryptfs ciphertext directory is created.
- The unlocked-folder picker chooses the parent directory where the decrypted mount will appear.
- The unlocked-folder picker starts in the same directory selected for encrypted storage.
- The decrypted mount appears as `<chosen-unlocked-parent>/Unlocked/<vault-name>`.

Both pickers browse within Umbrel's app data directory mounted at `/app-data`. This allows a mapped external folder such as `/app-data/external` to be selected.

The selected unlocked location is saved in persistent app metadata, keyed by vault. Existing vaults without metadata retain their previous mount-location behavior. Existing encrypted vault contents are not moved or modified.

## Publish/update

1. Replace `custom-apps-vault-manager/` in your GitHub repository with this folder.
2. Replace `.github/workflows/publish-vault-manager.yml` with the included workflow.
3. Commit changes and run the GitHub Actions workflow.
4. Ensure the GHCR package is Public.
5. Update Vault Manager in Umbrel.

Build tags: `1.0.9` and `latest`, for `linux/amd64` and `linux/arm64`.

Test with a new small vault first. Existing vaults keep their previous mount locations unless separately configured.
