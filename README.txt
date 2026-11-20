# Vault Manager GHCR publishing workflow

## Install it in your GitHub repository

1. Extract this ZIP.
2. In your `desantesway/umbrel-custom-apps` repository, upload the `.github` folder at the repository root.
   - If GitHub does not show hidden folders, create `.github/workflows/` manually and upload `publish-vault-manager.yml` there.
3. Commit the file.

The workflow supports either app folder name:
- `vault-manager/`
- `custom-apps-vault-manager/`

## Run it

1. Open the repository's **Actions** tab.
2. Select **Publish Vault Manager image**.
3. Choose **Run workflow**.
4. Wait for the workflow to complete successfully.

It publishes these tags:
- `ghcr.io/desantesway/vault-manager:1.0.0`
- `ghcr.io/desantesway/vault-manager:latest`

The workflow uses GitHub's automatic `GITHUB_TOKEN`; no personal access token is needed. The repository workflow permissions must allow the workflow to write packages.

## Important: make the package public

After the first successful publish, open the repository owner's GitHub **Packages** page, select `vault-manager`, open **Package settings**, and set package visibility to **Public**. Umbrel cannot pull a private package without registry credentials.

Then retry the Umbrel installation. The app's image reference must match:
`ghcr.io/desantesway/vault-manager:1.0.0`
