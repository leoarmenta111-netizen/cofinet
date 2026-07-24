# Restore guide

Restore scripts accept only local or QA targets and require explicit confirmation. They never target production.

## Restore production data into QA

Sanitize personal/payment data where policy requires and configure `.env.qa` with QA-only Mercado Pago and MikroTik credentials. Then run:

```bash
./scripts/restore-db.sh qa backups/production.dump --confirm-restore
```

```powershell
.\scripts\restore-db.ps1 -Environment qa -DumpPath .\backups\production.dump -ConfirmRestore
```

Plain `.sql` and custom `.dump`/`.backup` files are supported. The script stops the selected app tier, recreates only its isolated database, then restores; SQL restores use a transaction with stop-on-error. Start the environment again after verification.

After restore, verify table counts, health, login, plans, and admin read paths. Do not send real webhooks, payments, or RouterOS commands from restored production data.

Production disaster recovery requires a separate peer-reviewed runbook, approved outage, confirmed target, verified backup, and recovery-point decision. The convenience scripts deliberately do not implement it.
