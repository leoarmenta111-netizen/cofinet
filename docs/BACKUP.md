# Backup guide

Backups use PostgreSQL custom format and exclude ownership/privileges for portable QA restores. Files are written under ignored `backups/`.

Linux/WSL:

```bash
./scripts/backup-db.sh qa
./scripts/backup-db.sh prod
```

Windows PowerShell:

```powershell
.\scripts\backup-db.ps1 -Environment qa
.\scripts\backup-db.ps1 -Environment prod
```

Verify a custom-format dump:

```bash
docker run --rm -v "$PWD/backups:/backups:ro" postgres:16-alpine pg_restore --list /backups/FILE.dump
```

Production policy should include encrypted off-host storage, retention, access logging, checksums, and scheduled QA restore drills. A backup is not proven until it restores and smoke tests pass.

