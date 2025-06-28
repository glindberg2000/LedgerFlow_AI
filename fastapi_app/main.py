from fastapi import FastAPI
from .routers import users, accounts, statements, transactions, upload, dashboard

app = FastAPI(title="LedgerFlow FastAPI Backend")

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(upload.router)
app.include_router(dashboard.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
