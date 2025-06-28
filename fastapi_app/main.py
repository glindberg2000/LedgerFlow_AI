from fastapi import FastAPI
from .routers import (
    users,
    accounts,
    statements,
    transactions,
    uploads,
    dashboard,
    business_profiles,
    agents,
)
from .routers.agents import tools_router

app = FastAPI(title="LedgerFlow FastAPI Backend")

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(uploads)
app.include_router(dashboard.router)
app.include_router(business_profiles.router)
app.include_router(agents.router)
app.include_router(tools_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
