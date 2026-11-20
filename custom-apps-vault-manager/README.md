# Vault Manager — remove the unexpected app-password prompt

This revision removes the extra dashboard sign-in screen. The earlier package expected an `APP_PASSWORD` environment variable that was never configured by your Umbrel app installation, so it could not know a password you had chosen.

The app now opens directly through Umbrel's app proxy. Each encrypted vault still has its own password, entered when creating and unlocking that vault. This does not remove encryption from vault contents.

## Update steps

1. Replace the contents of `custom-apps-vault-manager/` in your GitHub repository with this folder.
2. Commit the changes.
3. Replace `.github/workflows/publish-vault-manager.yml` with the workflow included in this ZIP.
4. Run the GitHub Actions workflow and wait for a successful build.
5. Ensure the GHCR package is Public.
6. Update/reinstall Vault Manager from your Umbrel custom app store.

The app version and image tag are bumped to `1.0.1` so Umbrel pulls the new image.

Important: this removes the separate app login. Access is expected to be protected by Umbrel's own authenticated app proxy. Do not expose the app's container port directly to the internet.
