# Vault Manager 1.0.3

Fixes gocryptfs unlock command by removing the unsupported `-o uid=1000,gid=1000` argument. Adds a Toshiba-drive file picker: browse the drive, select files/folders, and copy them into an unlocked vault. The source drive is mounted read-only inside the app; the encrypted vault directory is hidden from the source picker.

## Build/publish
Replace the app folder in your GitHub repo, update the workflow to publish `ghcr.io/desantesway/vault-manager:1.0.3` for `linux/amd64,linux/arm64`, run Actions, and keep the GHCR package public.

## Safety
Existing encrypted vault data is not deleted or recreated. Selected files are copied, not moved, and existing destination names are skipped. Keep a separate backup of important data and recovery keys. This generated build has been syntax-checked but not tested on the Umbrel hardware; verify unlock and file copy with a disposable test vault/file first.
