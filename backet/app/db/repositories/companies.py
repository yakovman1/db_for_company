from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Company, CompanyUser


async def get_company(session: AsyncSession, *, company_id: str) -> Company | None:
    stmt = select(Company).where(Company.company_id == company_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count_company_users(session: AsyncSession, *, company_id: str) -> int:
    stmt = select(func.count()).select_from(CompanyUser).where(CompanyUser.company_id == company_id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def is_windows_user_allowed(session: AsyncSession, *, company_id: str, windows_user: str) -> bool:
    stmt = select(CompanyUser).where(
        CompanyUser.company_id == company_id,
        CompanyUser.windows_user == windows_user,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
