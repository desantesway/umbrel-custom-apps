# Vault Manager 1.0.2 — syntax and dashboard fix

This package fixes a malformed Python template boundary that caused:
`SyntaxError: invalid syntax` at `BROWSE = r"""`.

It also removes the stale APP_PASSWORD environment entry and fixes the dashboard so vaults are listed without a separate app login.

## Update
1. Replace the entire `custom-apps-vault-manager/` folder in your GitHub repository with this folder.
2. Replace `.github/workflows/publish-vault-manager.yml` with the included workflow.
3. Commit.
4. Run the GitHub Actions workflow and wait for a green success.
5. Make sure the GHCR package `vault-manager` is Public.
6. Update/reinstall the app in Umbrel. The app/image version is now 1.0.2.

The workflow builds `linux/amd64` and `linux/arm64`.
The app's encrypted vault passwords are unchanged; this patch only fixes dashboard startup/login handling.
