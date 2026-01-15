"""
Validation Engine - Accuracy guardrails before export.

Validates:
- Invoice totals = sum(line items)
- GSTIN format valid
- State code matches GSTIN
- Tax logic consistent (IGST vs CGST/SGST)
"""
