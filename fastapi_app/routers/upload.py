from fastapi import APIRouter, UploadFile, File, HTTPException, status
from ..services import parser
import shutil
import os

router = APIRouter(prefix="/upload", tags=["upload"])

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
