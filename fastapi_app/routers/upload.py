from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db import SessionLocal
from typing import List, Dict, Any
from ..services import parser
import shutil
import os
import traceback
from rich import print as rich_print

# Add parser registry imports
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../PDF-extractor"))
)
from dataextractai.parsers_core.autodiscover import autodiscover_parsers
from dataextractai.parsers_core.registry import ParserRegistry

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/")
def upload_statement(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Call the parser service (placeholder)
    result = parser.run_parser_on_file(file_path)
    return {"filename": file.filename, "parser_result": result}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[Dict[str, Any]])
def list_uploads(db: Session = Depends(get_db)):
    try:
        # Raw SQL join to get all uploads with parsing and processing info
        q = db.execute(
            text(
                """
                SELECT f.id as file_id,
                       f.file as file_name,
                       f.file_type as file_type,
                       f.status as file_status,
                       pr.parser_module,
                       pr.status as parsing_status,
                       pr.error_message,
                       pr.rows_imported,
                       pr.created as parsing_created,
                       pt.task_id as processing_task_id,
                       pt.status as processing_status,
                       pt.task_type,
                       pt.created_at as processing_created,
                       pt.updated_at as processing_updated,
                       pt.transaction_count,
                       pt.processed_count,
                       pt.error_count,
                       pt.error_details,
                       pt.task_metadata,
                       pt.client_id as processing_client_id
                FROM profiles_uploadedfile f
                LEFT JOIN profiles_parsingrun pr ON f.id = pr.statement_file_id
                LEFT JOIN profiles_processingtask pt ON pt.task_metadata::text LIKE '%' || f.id || '%'
                ORDER BY f.id DESC
                """
            )
        )
        return [dict(row._mapping) for row in q]
    except Exception as e:
        rich_print(f"[red]Exception in /uploads/: {e}[/red]")
        rich_print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsers", response_model=List[str])
def list_parsers():
    autodiscover_parsers()
    return ParserRegistry.list_parsers()
