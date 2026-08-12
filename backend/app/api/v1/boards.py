from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.ids import new_board_id
from app.core.security import get_current_user
from app.models.board import Board
from app.models.user import User
from app.schemas.api import BoardCreate, BoardResponse

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("", response_model=BoardResponse, status_code=201)
async def create_board(
    body: BoardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.board_id:
        board_id = body.board_id
    else:
        count_result = await db.execute(select(func.count()).select_from(Board))
        seq = (count_result.scalar_one() or 0) + 1
        board_id = new_board_id(seq)

    board = Board(board_id=board_id)
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return board
