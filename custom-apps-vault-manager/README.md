# Vault Manager 1.0.5 — stale FUSE mount fix

Fixes the dashboard Internal Server Error caused by `location_options()` recursively scanning `Vault/Unlocked` and calling `stat()` on a disconnected FUSE mount (OSError 107: Transport endpoint is not connected).

The location picker now deliberately skips the entire `Unlocked` tree and catches filesystem errors while enumerating storage folders. Existing encrypted vault data and vault locations are not migrated or modified.

## Update

1. Replace `custom-apps-vault-manager/` in your GitHub repository with this folder.
2. Replace `.github/workflows/publish-vault-manager.yml` with the included workflow.
3. Commit, then run **Actions → Publish Vault Manager image**.
4. Wait for success and update/reinstall the app in Umbrel.

The image tag and app version are `1.0.5` and the workflow builds both `linux/amd64` and `linux/arm64`.

## If the old disconnected mount remains

After the new version is running, if the `Person` mount still reports a transport endpoint error, try detaching only that stale mount from inside the container:

`sudo docker exec custom-apps-vault-manager_server_1 fusermount3 -uz /vault/Unlocked/Person`

Do not delete the encrypted `Person` directory under `/vault`; it contains the encrypted vault data.
