# Source Inventory

This directory records where the canonical repository content came from and
why each source was included, reviewed, or excluded.

The inventory is intentionally kept in the repository so later maintenance can
trace a file back to its original project without relying on this Mac's
directory layout.

## Classification

- `include`: reusable source, benchmark definitions, tests, schemas, or
  documentation copied into the canonical tree.
- `example-only`: a small, reviewed artifact kept to demonstrate the result
  format or workflow.
- `review`: potentially sensitive, large, licensed, or ambiguous material that
  is preserved outside the tracked canonical source until explicitly reviewed.
- `exclude`: local credentials, virtual environments, caches, browser state,
  generated logs, and disposable build artifacts.

The original source directories are not deleted by consolidation scripts.
