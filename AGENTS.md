# Repository Agent Notes

- Treat environment presets as SDK contract data, not deployment-readiness or
  general-availability claims. While hosted access is private, public examples
  must use onboarding-provisioned issuer and credential values, start with
  `staging`, and describe `production` targets as reserved unless readiness and
  access are explicitly approved.
- Edit `scripts/gen-sdk-docs.py`, then regenerate `docs/site/`; never hand-edit
  the generated Mintlify files.
