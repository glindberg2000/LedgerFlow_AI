from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Agent as AgentModel
from ..schemas import Agent as AgentSchema
from sqlalchemy import select
from typing import List
from ..models import Tool as ToolModel, LLMConfig as LLMConfigModel

router = APIRouter(prefix="/agents", tags=["agents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[dict])
def list_agents(db: Session = Depends(get_db)):
    # Join Agent, LLMConfig, and tools
    agents = db.execute(
        """
        SELECT a.id, a.name, a.purpose, a.prompt, a.llm_id, l.model as llm_name
        FROM profiles_agent a
        LEFT JOIN profiles_llmconfig l ON a.llm_id = l.id
        """
    ).fetchall()
    agent_list = []
    for a in agents:
        # Get tool names for each agent
        tools_q = db.execute(
            """
            SELECT t.name FROM profiles_tool t
            JOIN profiles_agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = :agent_id
            """,
            {"agent_id": a.id},
        )
        tool_names = [row[0] for row in tools_q]
        agent_list.append(
            {
                "id": a.id,
                "name": a.name,
                "purpose": a.purpose,
                "prompt": a.prompt,
                "llm_id": a.llm_id,
                "llm_name": a.llm_name,
                "tools": tool_names,
            }
        )
    return agent_list


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
