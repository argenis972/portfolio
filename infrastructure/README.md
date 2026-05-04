# Infrastructure Provisioning

This setup is intentionally minimal to prioritize clarity over full infrastructure automation. This setup prioritizes reproducibility of the backend service, not full infrastructure parity.

## Scope

What is provisioned:
- Koyeb Application (`argenis-portfolio`)
- Koyeb Service (`api`) mapping to the root Dockerfile
- All required environment variables (via `TF_VAR_*`)
- Health checks and auto-restart policies

What is **intentionally NOT** provisioned (out of scope):
- **Upstash Redis**: No official Terraform provider, must be configured manually.
- **Supabase PostgreSQL**: Requires complex manual setup for the free tier, intentionally skipped to keep IaC minimal.
- **Vercel Frontend**: Already configured via `vercel.json` and GitHub integration.

## Prerequisites

Before running any Terraform commands, you MUST expose your secrets to the local environment so Terraform can use them without committing them to the code.

```bash
# Windows (PowerShell)
$env:TF_VAR_koyeb_token="your-koyeb-token"
$env:TF_VAR_database_url="your-db-url"
$env:TF_VAR_redis_url="your-redis-url"
$env:TF_VAR_sentry_dsn="your-sentry-dsn"

# Linux/macOS
export TF_VAR_koyeb_token="your-koyeb-token"
export TF_VAR_database_url="your-db-url"
export TF_VAR_redis_url="your-redis-url"
export TF_VAR_sentry_dsn="your-sentry-dsn"
```

## Bootstrap from scratch (< 10 commands)

1. Set your `TF_VAR_*` variables as shown above.
2. Initialize Terraform:
   ```bash
   terraform init
   ```
3. Review the execution plan:
   ```bash
   terraform plan
   ```
4. Apply the configuration:
   ```bash
   terraform apply
   ```

The application will be deployed and available at the URL shown in the `Outputs`.
