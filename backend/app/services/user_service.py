import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await UserRepository.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )
        return user

    async def list_users(self, skip: int = 0, limit: int = 100, role: Optional[str] = None) -> List[User]:
        return await UserRepository.list_users(self.db, skip=skip, limit=limit, role=role)

    async def create_user(self, user_in: UserCreate) -> User:
        existing = await UserRepository.get_by_email(self.db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{user_in.email}' already exists",
            )
        return await UserRepository.create(self.db, user_in)

    async def update_user(self, user_id: uuid.UUID, user_in: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        if user_in.email and user_in.email != user.email:
            existing = await UserRepository.get_by_email(self.db, user_in.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{user_in.email}' is already taken",
                )
        return await UserRepository.update(self.db, user, user_in)
