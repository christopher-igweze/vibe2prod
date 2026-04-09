"""Pydantic models — organized by bounded context.

Subdirectories provide grouped imports:
  - models.scanning  — scan, findings, evolution
  - models.execution — builds, runtime, agent logs
  - models.user      — onboarding, credits

All original module-level imports remain valid:
  from models.scan import AuditRequest      # still works
  from models.scanning import AuditRequest  # also works
"""
