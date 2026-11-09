from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.csv_import import MissingColumns, parse_csv
from app.db import get_session
from app.deps import require_role
from app.import_service import assignment_table, run_import
from app.models import Branch, Role, User

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("")
async def import_overdue_csv(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    manager: User = Depends(require_role(Role.branch_manager)),
):
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, {"code": "file_too_large"})
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, {"code": "not_utf8"})

    branches = (await session.scalars(select(Branch))).all()
    known_pincodes = {p for b in branches for p in b.pincodes}
    try:
        parsed = parse_csv(text, known_pincodes, date.today())
    except MissingColumns as e:
        raise HTTPException(400, {"code": "missing_columns", "columns": e.missing})
    # an empty file would otherwise mark every loan as cured
    if parsed.total_rows == 0:
        raise HTTPException(400, {"code": "empty_file"})

    summary = await run_import(session, parsed, branches)
    table = await assignment_table(session, summary.new_by_officer)
    await session.commit()
    return {
        "file_name": file.filename,
        "file_size": len(data),
        "rows": parsed.total_rows,
        "imported": summary.created + summary.updated,
        "created": summary.created,
        "updated": summary.updated,
        "not_imported": parsed.invalid_rows,
        "assigned": summary.created,
        "cured": summary.cured,
        "errors": [e.__dict__ for e in parsed.errors],
        "assignment": table,
    }
