# Binder Refactor Plan for Django Admin

## Overview

This document outlines a step-by-step plan to evolve the current Django admin setup (centered on BusinessProfile and flat checklists/attachments) into a binder-centric model. The goal is to improve clarity, scalability, and future extensibility (including a possible client portal), while allowing the existing admin to remain as a backup during the transition.

---

## 1. Rationale for the Binder Model

- **Current Pain Points:**
  - All client data is managed in a flat structure, making it hard to focus on a single client or year.
  - Attachments and checklists are not explicitly grouped by year/engagement.
  - No clear dashboard for "what's missing" or progress per client-year.
- **Binder Model Benefits:**
  - Each client-year (engagement) is a "binder"—a focused workspace for all docs, checklists, and reports.
  - Enables hierarchical navigation: Client → Year → Binder Dashboard.
  - Supports future client/contributor portal with minimal changes.
  - Allows parallel operation of old and new UIs for safe migration.

---

## 2. Current Implementation Summary (as of latest review)

- **No critical data in the current DB**; only a bootloader/sample client, which can be wiped as needed.
- **BusinessProfile**: Represents a client.
- **TaxChecklistItem**: Represents a checklist item for a client and a specific tax year (tax_year is a CharField, not a FK to a TaxYear model).
  - Linked to BusinessProfile via FK.
  - Attachments are managed via a separate ChecklistAttachment model (not as a FileField on TaxChecklistItem).
- **ChecklistAttachment**: Linked to TaxChecklistItem via FK. Stores file, tag, and upload date.
- **No explicit TaxYear or BinderSection model.**
- **Admin UI**: Supports year filtering, checklist management, and attachment management. Templates provide controls for year selection and checklist initialization/reset.
- **Checklist Initialization**: Management command and admin UI allow initializing checklist items for a client and year from a canonical JSON index.
- **No grouping of checklist items into sections (e.g., Organizer, P&L, etc.).**

---

## 3. Data Model Evolution

### **A. New/Refined Models**

- **BusinessProfile**: (existing) Represents a client.
- **TaxYear**: New. Represents a binder for a client and year (e.g., 2023, 2024).
  - Fields: client (FK to BusinessProfile), year (int), status, notes, etc.
- **BinderSection**: (optional) Groups checklist items within a binder (e.g., Organizer, P&L, Crypto).
- **ChecklistItem**: Now linked to BinderSection (or directly to TaxYear if sections are skipped).
  - Fields: section (FK), name, required, status (missing, received, etc.).
- **Attachment/Document**: Linked to ChecklistItem and TaxYear.
  - Fields: checklist_item (FK), tax_year (FK), file, metadata.
- **Report/CalculationResult**: Linked to TaxYear and ChecklistItem.

### **B. Migration Steps**

1. **Add TaxYear model** and update relationships in ChecklistItem, Attachment, and Report.
2. **Data migration:** Assign all existing checklist items and attachments to a default year (e.g., 2023) for current data.
3. **(Optional) Add BinderSection model** and update checklist items to use it.
4. **Update admin.py** to support new relationships and navigation.

---

## 4. Bootloader & Sample Data Strategy

- Since there is no critical data, the bootloader/sample client can be wiped and reloaded as needed.
- **Enhance the bootloader** to create multiple binders (years) for the sample client, demonstrating how the binder model works in practice.
- This will make it clear in the UI how multiple years/engagements are managed for a single client.

---

## 5. Admin UI Refactor

- **Navigation:**
  - Filter by client, then by year (TaxYear), then show binder dashboard.
- **Binder Dashboard:**
  - Progress bar or summary at the top (e.g., "8/12 items complete").
  - Sections (tabs or accordions) for Organizer, P&L, etc.
  - Each section lists checklist items, their status, and actions (upload, generate, mark complete).
  - Attachments and reports shown inline or as links.
- **Quick Actions:**
  - Upload, generate, or mark as complete for each checklist item.
- **Status Indicators:**
  - Color coding or icons for missing, received, in review, complete.

---

## 6. Parallel UI Strategy

**Options for running the new binder UI in parallel with the existing admin:**

### A. New Django App (Recommended for Clean Separation)
- Create a new Django app (e.g., `binders` or `client_portal`) with its own models, views, templates, and URLs.
- Register new models/admins as needed.
- Pros: Clean separation, easy to test and iterate, can be enabled/disabled independently.
- Cons: Slightly more setup, but minimal risk to existing admin.

### B. New Admin Site
- Use Django's `AdminSite` to create a separate admin interface for the binder model.
- Pros: Both old and new admin UIs can run on different URLs (e.g., `/admin/` and `/binder-admin/`).
- Cons: More admin.py boilerplate, but keeps legacy admin untouched.

### C. New Navigation Section in Existing Admin
- Add binder navigation as a new section or dashboard in the current admin.
- Pros: Familiar for current users, minimal setup.
- Cons: Can get cluttered, risk of confusion during transition.

### D. Separate Git Branch
- Develop the binder model and UI in a feature branch.
- Pros: No risk to production, can merge when ready.
- Cons: Can't run both UIs in production at the same time unless you merge.

**Best Practice:**
- Use a new Django app or admin site for the binder UI, and develop in a feature branch for safety. This allows you to run both UIs in parallel for testing and transition.

---

## 7. Future-Proofing for a Client Portal

- **All new models and relationships** are designed to support a public or contributor portal.
- **Permissions** can be managed so clients/contributors only see their own binders.
- **Portal UI** can reuse binder dashboard logic for a client-friendly experience.

---

## 8. Migration/Refactor Checklist

- [ ] Add TaxYear model and update relationships.
- [ ] Migrate existing data to use TaxYear (default year for legacy data).
- [ ] (Optional) Add BinderSection model and update checklist items.
- [ ] Update admin.py for new navigation and dashboard features.
- [ ] Implement progress/status indicators.
- [ ] Build new UI/admin for binder model.
- [ ] Test data migration and parallel operation.
- [ ] Enhance bootloader to create multiple binders for sample client.
- [ ] Document new structure for future portal development.

---

## 9. Timeline Estimate

- **Models:** 1–2 days (including data migration scripts)
- **Admin/UI:** 1–2 days (navigation, filters, inlines, progress)
- **Testing & Data Migration:** 1 day
- **Total:** ~3–5 days for a robust, future-proof refactor

---

## 10. Next Steps

1. Review current models and relationships.
2. Implement TaxYear and update related models.
3. Refactor admin UI for binder-centric navigation.
4. Enhance bootloader/sample data to show multiple binders.
5. Test and validate parallel operation.
6. Prepare for PRD and portal planning. 