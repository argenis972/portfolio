## What & Why

<!-- What changed and what forced this change now. One paragraph.
     If this resolves an incident: link it → Closes INC-XXX
     If this adds an ADR-worthy decision: link it → See ARCHITECTURE.md ADR-XX -->

## Type of change

- [ ] `feat` · [ ] `fix` · [ ] `perf` · [ ] `refactor` · [ ] `chore` · [ ] `docs` · [ ] `ci`

## Consequences accepted

<!-- What does this fix break or constrain? What trade-off was made?
     "None" is a valid answer for small changes — but it must be a conscious answer. -->

## Definition of Done

- [ ] `ruff` + `mypy` pass locally
- [ ] New logic has unit tests (`test_<unit>_<scenario>_<expected_result>`)
- [ ] `CHANGELOG.md` updated if behavior changed
- [ ] `ARCHITECTURE.md` updated if an ADR-worthy decision was made
- [ ] `.env.example` updated if new environment variables were added
- [ ] No placeholders, no TODO comments, no dead code

## How to test

<!-- Concrete steps. Not "run the app and check" — specific endpoint, payload, expected response. -->

```bash
# example
curl -X POST https://api.argenisbackend.com/api/v1/contact \
  -H "Idempotency-Key: test-123" \
  -d '{"name": "Test", "email": "t@t.com", "subject": "x", "message": "y"}'
# expected: 202 with queue_status field
```

## Observability impact

<!-- Did this change what gets logged, traced, or measured?
     New log fields? Modified metric labels? New Sentry context?
     Skip if no observability changes. -->

## Screenshots

<!-- UI changes only. Skip otherwise. -->
