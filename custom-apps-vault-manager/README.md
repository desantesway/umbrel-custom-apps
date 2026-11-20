# Vault Manager 1.0.4

Adds a vault storage-folder selector and permanent deletion for locked vaults. Vaults can be stored in subfolders under `/vault`; unlocked mounts mirror their relative paths under `/vault/Unlocked`. Delete requires the vault to be locked and the user to type `DELETE`. Deletion permanently removes the encrypted vault data.

Update by replacing the app folder and workflow in your repository, committing, running GitHub Actions, and updating the app in Umbrel. Keep backups of encrypted vaults and recovery keys.
