from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Agent as AgentModel
from ..schemas import Agent as AgentSchema
from sqlalchemy import select
from typing import List
from ..models import Tool as ToolModel

router = APIRouter(prefix="/agents", tags=["agents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[AgentSchema])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(AgentModel).all()
    return [
        AgentSchema(
            id=a.id,
            name=a.name,
            purpose=a.purpose,
            prompt=a.prompt,
            llm_id=a.llm_id,
        )
        for a in agents
    ]


@router.get("/{agent_id}/tools", response_model=List[dict])
def get_agent_tools(agent_id: int, db: Session = Depends(get_db)):
    # Join profiles_agent_tools and profiles_tool
    q = db.execute(
        """
        SELECT t.id, t.name, t.description, t.module_path, t.created_at, t.updated_at
        FROM profiles_tool t
        JOIN profiles_agent_tools at ON t.id = at.tool_id
        WHERE at.agent_id = :agent_id
        """,
        {"agent_id": agent_id},
    )
    return [dict(row) for row in q]


# Standalone tools endpoint
from fastapi import APIRouter as ToolsAPIRouter

tools_router = ToolsAPIRouter(prefix="/tools", tags=["tools"])


@tools_router.get("/", response_model=List[dict])
def list_tools(db: Session = Depends(get_db)):
    tools = db.query(ToolModel).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "module_path": t.module_path,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }
        for t in tools
    ]
