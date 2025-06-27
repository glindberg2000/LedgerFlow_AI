# LedgerFlow: FastAPI + React Modern Rebuild

## Overview
This branch is dedicated to rebuilding LedgerFlow as a modern, scalable, multi-user web platform using **FastAPI** (Python) for the backend and **React** (TypeScript) for the frontend. The goal is to preserve all core business logic and data from the legacy Django system, while delivering a beautiful, robust, and maintainable user experience.

---

## Migration Goals
- **Eliminate Django admin recursion and legacy limitations**
- **Modernize the UI/UX** with React and a component library (Material UI, Ant Design, or Tailwind)
- **Expose all business logic and data via FastAPI endpoints**
- **Retain and extend all core features:**
  - Statement upload (PDF/CSV)
  - Pluggable parser integration (Python modules)
  - Transaction management and batch processing (AI/agents)
  - Reporting (6A worksheet, exports, dashboard)
  - Multi-user authentication and permissions
  - Background processing (Celery or FastAPI background tasks)

---

## Main Features (to be implemented)
1. **User Authentication & Roles** (JWT, OAuth2)
2. **Statement Upload & Parsing** (drag-and-drop, progress, error feedback)
3. **Transaction Table** (filter, search, batch select, edit)
4. **AI/Agent Batch Processing** (trigger jobs, monitor progress, logs)
5. **Reporting & Dashboard** (6A worksheet, CSV/XLSX/PDF export, stats)
6. **Admin Panel** (users, agents, parsers, business profiles)
7. **Parser Registry** (pluggable, extensible)
8. **Background Task System** (Celery or FastAPI background tasks)

---

## Architecture Plan
- **Backend:** FastAPI + SQLAlchemy (models to match legacy DB)
- **Frontend:** React (TypeScript) + UI library
- **Background Jobs:** Celery (with Redis/RabbitMQ) or FastAPI background tasks
- **Parser Integration:** Import Python modules or microservices
- **Reporting:** SQL queries, aggregation endpoints, export APIs

---

## Data Source
- **Legacy Django/Postgres DB** is the source of truth for all business data and logic.
- All migrations and new features should be compatible with the existing schema, or provide migration scripts as needed.

---

## Next Steps for the New Agent/Team
1. Review this README and the legacy Django models and business logic.
2. Scaffold FastAPI models and endpoints to match the current DB schema.
3. Scaffold React app with authentication, dashboard, and upload flows.
4. Integrate background processing and parser modules.
5. Rebuild reporting and admin features.
6. Test with legacy data and iterate.

---

## Handoff Notes
- The legacy system and codebase are available for reference.
- Ask for any code samples, DB schema, or business logic details as needed.
- This branch is isolated from all debug and legacy admin code.

---

**Contact:**
- For questions, context, or code samples, ping the main dev or spin up a direct agent chat. 