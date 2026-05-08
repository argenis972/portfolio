# Incident Post-Mortem: INC-009

## 🛑 Secret Identity Collision (Rename Race Condition)

**Date**: 2026-05-08
**Version**: v1.8.1
**Component**: Infrastructure (Terraform / Koyeb)
**Impact**: Deployment failure in CI/CD pipeline (Blocked `terraform apply`).

### Summary
During the "English-First" standardization, several Terraform resource keys in the `secrets_registry` were renamed (e.g., `ENVIRONMENT` → `AMBIENTE`). While the application-facing keys were correctly updated, the change in Terraform resource IDs triggered a `destroy + create` cycle. Since both the old and new resources mapped to the same physical secret name in Koyeb, the creation of the new secret failed because the name already existed.

### Root Cause
Terraform does not recognize a key change in a `for_each` map as a "rename". It treats it as the deletion of one instance and the creation of another. In parallel execution, the "create" step often hits the API before the "destroy" step is fully processed, or simply conflicts with the existing resource.

### Resolution
Implemented Terraform `moved` blocks to explicitly map the old resource IDs to the new ones in the state. This converted the `destroy + create` operation into a safe `rename` (state-only update), resulting in "0 to destroy" in the plan.

### Lessons Learned
- **Renaming is Destructive**: In Terraform, renaming a resource key is a destructive operation by default.
- **"Zero to Destroy" Principle**: Any unexpected `destroy` in a plan for stable resources (secrets, DBs) must be treated as a critical risk.
- **State Migration**: Use `moved` blocks whenever refactoring resource keys in maps.
