# Incident Post-Mortem: INC-007
## 🛑 Koyeb Terraform Provider Schema Incompatibility

**Date:** 2026-05-07  
**Severity:** P1 (Infrastructure Blocked)  
**Status:** Resolved (via Architectural Pivot)

---

### 📝 Executive Summary
During the migration from manual deployment to Infrastructure as Code (IaC) using Terraform, the deployment pipeline was blocked by a critical schema mismatch between the `koyeb/koyeb` Terraform provider (v0.1.11) and the modern Koyeb API. The provider lacked support for the newly mandatory `type` field in environment variable definitions, resulting in a permanent `400 Bad Request`.

### 🔍 Symptoms
- **Terraform Error:** `{"field":"definition.env.***.type", "description":"env type is required"}`.
- **Context:** The error persisted even after removing all unsupported arguments from the HCL code, indicating that the provider was sending an incomplete JSON payload to the API.
- **Impact:** Automated infrastructure provisioning was impossible, stalling the v1.7.0 release.

### 🕵️ Root Cause Analysis
1.  **Abstractions Leak:** The Terraform provider (v0.1.11) was last updated in early 2024.
2.  **API Evolution:** The Koyeb API evolved to require an explicit `type` (`PLAINTEXT` or `SECRET`) for all environment variables within a service definition.
3.  **Schema Rigidity:** Because the provider's HCL schema did not include a `type` field for the `env` block, there was no way to pass the required metadata through standard configuration.

### 🛡️ Mitigation & Architectural Pivot
Instead of waiting for a provider update (which was outside our control), we implemented a **Secret-First Orchestration** strategy:

1.  **Koyeb Secrets Vault:** Every environment variable (sensitive or not) was moved into a `koyeb_secret` resource.
2.  **Reference-Only Injection:** The `koyeb_service` was refactored to use only `secret` references instead of literal `value` keys.
3.  **Why it worked:** The Koyeb API handles secret references differently; since the secret itself already has an immutable type in the vault, the service definition API does not require the `type` field for that specific environment entry.

### 📈 Reliability Enhancements
As a side effect of this incident, we introduced **Resilient Provisioning Logic**:
- **Filtering Logic:** Added a Terraform `locals` filter to automatically omit empty/null variables from the provisioning loop. This prevents the "cannot use <nil>" API error when optional GitHub Secrets are missing.
- **Nonsensitive Key Mapping:** Solved the `Invalid for_each argument` error by decoupling sensitive values from non-sensitive resource keys, ensuring a clean and secure Terraform state.

### 💡 Lessons Learned
- **Don't fight the tooling, bypass it:** When a managed provider is broken, look for alternative resource paths (Secrets vs. Env) that the API might handle more gracefully.
- **Infrastructure is Code:** Just like application code, infrastructure needs defensive programming (filtering, error handling, and type safety).
