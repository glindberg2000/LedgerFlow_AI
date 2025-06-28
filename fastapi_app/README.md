# LedgerFlow FastAPI Backend

## Overview
This is the backend for the LedgerFlow rebuild, using FastAPI, SQLAlchemy, and Pydantic. It is designed for modern, robust, and maintainable financial statement management, with seamless integration to a React frontend and the PDF-extractor submodule.

## Features
- Modern FastAPI project structure
- SQLAlchemy ORM and Pydantic schemas
- JWT/OAuth2 authentication (coming soon)
- File upload and parser integration
- Modular routers for users, accounts, statements, transactions
- Designed for a slick, modern UI/UX (light/dark mode, best widgets)

## Setup
1. Create and activate a Python virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```sh
   pip install fastapi[all] sqlalchemy pydantic psycopg2-binary
   ```
3. Set up your `.env` file with the Postgres connection string:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/ledgerflow
   ```
4. Run the FastAPI app:
   ```sh
   uvicorn fastapi_app.main:app --reload
   ```

## API Endpoints
- `/health` — Health check
- `/users` — User registration/login (JWT coming soon)
- `/accounts` — Account CRUD
- `/statements` — Statement CRUD
- `/transactions` — Transaction CRUD
- `/upload` — File upload and parser integration

## PDF-extractor Integration
- The backend will call the PDF-extractor submodule to parse uploaded statements.
- Parser results are validated against Pydantic/JSON Schema contracts.

## UI/UX Goals
- The frontend (React) will use the best available widgets and design patterns.
- Light/dark mode and a polished, modern look are priorities.

---
For questions or to contribute, see the main project README or contact the dev team. 