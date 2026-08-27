# Infrastructure

Deployment and local infrastructure assets live here.

## Local PostgreSQL With Docker

```powershell
cd infra
docker compose up -d
```

Then run migrations from the repository root:

```powershell
.\scripts\setup_database.ps1
```
