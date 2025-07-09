# Organizer Manifest Ingest for Binder Checklist

## Overview

This feature ingests the output manifest (`all_fields_manifest_cleaned.json`) from the organizer workbook extraction pipeline and automatically generates actionable checklist items for the Binder (TaxYear) workflow. The goal is to provide CPAs and clients with a birdseye view of what information is prefilled, missing, needs review, or requires document uploads, streamlining the tax preparation process.

---

## Goals
- **Automate binder checklist creation** from extracted organizer data.
- **Flag critical items**: prefilled, missing, needs scan, needs calculation, etc.
- **Group checklist items by section** (Personal Info, Income, Deductions, etc.).
- **Enable actionable workflow** for CPAs and clients to review, complete, or upload required information.

---

## Inputs
- `all_fields_manifest_cleaned.json` (output from OrganizerExtractor)
- Associated OrganizerWorkbook and Binder (TaxYear) records

---

## Functional Requirements

### 1. Manifest Parsing
- Parse the manifest JSON, iterating over each page and its `data` fields.
- For each field/question:
  - Create a checklist item in the Binder (TaxYear) context.
  - Extract metadata: section, label, page number, field name, value, etc.

### 2. Checklist Item Generation
- **Prefilled fields**: Mark as "prefilled" and flag for review/confirmation.
- **Blank/required fields**: Mark as "missing" and flag for entry.
- **Calculated fields**: Mark as "auto-calculate" or "needs calculation".
- **Document requests**: For fields requiring uploads (e.g., W-2, 1099), create "needs scan" tasks.
- **Prior year data**: If present, auto-populate and flag for review.

### 3. Grouping and Organization
- Group checklist items by section/label (from manifest: `label`, `Title`).
- Allow filtering by status (missing, prefilled, needs scan, etc.).
- Link each item to the source page in the PDF for review.

### 4. UI/UX
- Display checklist in the Binder view, grouped by section.
- Show status indicators (prefilled, missing, needs scan, etc.).
- Allow users to mark items as complete, upload documents, or enter missing data.
- Provide links to the relevant PDF page or extracted data for context.

### 5. Automation & Updates
- On new organizer upload or re-extraction, re-ingest manifest and update checklist.
- Sync status if user updates a field or uploads a document.

---

## Non-Functional Requirements
- Ingestion should be idempotent and handle re-runs gracefully.
- Handle large manifests efficiently (hundreds of fields/pages).
- Log errors and flag any manifest parsing issues for review.

---

## Out of Scope
- Direct editing of the manifest JSON (source of truth is the extracted file).
- Full document viewer integration (future enhancement).

---

## Success Criteria
- After organizer extraction, the Binder checklist is auto-populated with actionable items.
- CPAs/clients can see at a glance what is prefilled, missing, or needs action.
- The workflow for binder prep is significantly faster and less error-prone. 