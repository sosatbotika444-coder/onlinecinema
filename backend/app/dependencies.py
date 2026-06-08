from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Participant
from app.security import bearer_token, decode_session_token


async def current_participant(
    token: str = Depends(bearer_token),
    db: AsyncSession = Depends(get_db),
) -> Participant:
    payload = decode_session_token(token)
    participant_id = payload.get("sub")
    participant = await db.get(Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session participant not found")
    return participant


async def require_room_participant(
    room_code: str,
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> Participant:
    result = await db.execute(select(Participant).where(Participant.id == participant.id))
    participant = result.scalar_one_or_none()
    if not participant or participant.room.code != room_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant is not in this room")
    return participant
