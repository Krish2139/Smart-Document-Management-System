from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from backend.models.document import Document
from backend.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: str) -> Optional[Document]:
        return self.get_by_id(entity_id)

    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[Document]:
        return self.get_all(skip=skip, limit=limit, **kwargs)

    def get_by_id(self, entity_id: str) -> Optional[Document]:
        return self.db.execute(select(Document).where(Document.id == entity_id)).scalar_one_or_none()

    def get_by_hash(self, sha256_hash: str, user_id: Optional[str] = None) -> Optional[Document]:
        stmt = select(Document).where(Document.sha256_hash == sha256_hash)
        if user_id:
            stmt = stmt.where(Document.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def _build_filter_conditions(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        user_id: Optional[str] = None,
    ):
        conditions = []

        if user_id:
            conditions.append(Document.user_id == user_id)
        else:
            conditions.append(Document.user_id.is_(None))

        if query:
            clean_q = query.strip().lstrip('.').lower()
            q_like = f"%{clean_q}%"
            conditions.append(
                or_(
                    func.lower(Document.filename).like(q_like),
                    func.lower(Document.original_filename).like(q_like),
                    func.lower(Document.file_extension).like(q_like),
                    func.lower(Document.category_name).like(q_like),
                    func.lower(Document.file_type).like(q_like)
                )
            )

        if category and category.lower() != "all":
            conditions.append(func.lower(Document.category_name) == category.lower())

        if file_type and file_type.lower() != "all":
            conditions.append(func.upper(Document.file_type) == file_type.upper())

        if file_extension and file_extension.lower() != "all":
            ext = file_extension.lstrip('.').lower()
            conditions.append(func.lower(Document.file_extension) == ext)

        if date_from:
            conditions.append(Document.created_at >= date_from)

        if date_to:
            conditions.append(Document.created_at <= date_to)

        if min_size is not None and min_size >= 0:
            conditions.append(Document.file_size >= min_size)

        if max_size is not None and max_size > 0:
            conditions.append(Document.file_size <= max_size)

        return conditions

    def _apply_sorting(self, stmt, sort_by: str = "date", sort_order: str = "desc"):
        is_asc = sort_order.lower() == "asc"
        sb = sort_by.lower()

        if sb in {"name", "filename"}:
            return stmt.order_by(Document.filename.asc() if is_asc else Document.filename.desc())
        elif sb in {"size", "file_size"}:
            return stmt.order_by(Document.file_size.asc() if is_asc else Document.file_size.desc())
        elif sb in {"category", "category_name"}:
            return stmt.order_by(Document.category_name.asc() if is_asc else Document.category_name.desc())
        else:  # default date / created_at
            return stmt.order_by(Document.created_at.asc() if is_asc else Document.created_at.desc())

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        user_id: Optional[str] = None
    ) -> List[Document]:
        stmt = select(Document)
        conditions = self._build_filter_conditions(
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = self._apply_sorting(stmt, sort_by=sort_by, sort_order=sort_order)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(
        self,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> int:
        stmt = select(func.count(Document.id))
        conditions = self._build_filter_conditions(
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return self.db.execute(stmt).scalar() or 0

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> List[Document]:
        stmt = select(Document)
        conditions = self._build_filter_conditions(
            query=query,
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = self._apply_sorting(stmt, sort_by=sort_by, sort_order=sort_order)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_search(
        self,
        query: str,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> int:
        stmt = select(func.count(Document.id))
        conditions = self._build_filter_conditions(
            query=query,
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return self.db.execute(stmt).scalar() or 0

    def get_total_size(self, user_id: Optional[str] = None) -> int:
        stmt = select(func.coalesce(func.sum(Document.file_size), 0))
        if user_id:
            stmt = stmt.where(Document.user_id == user_id)
        else:
            stmt = stmt.where(Document.user_id.is_(None))
        return self.db.execute(stmt).scalar() or 0

    def get_file_type_counts(self, user_id: Optional[str] = None) -> List[tuple]:
        stmt = select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)
        if user_id:
            stmt = stmt.where(Document.user_id == user_id)
        else:
            stmt = stmt.where(Document.user_id.is_(None))
        stmt = stmt.order_by(func.count(Document.id).desc())
        return list(self.db.execute(stmt).all())

    def get_recent(self, limit: int = 5, user_id: Optional[str] = None) -> List[Document]:
        stmt = select(Document)
        if user_id:
            stmt = stmt.where(Document.user_id == user_id)
        else:
            stmt = stmt.where(Document.user_id.is_(None))
        stmt = stmt.order_by(Document.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, entity_data: dict) -> Document:
        doc = Document(**entity_data)
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update(self, entity_id: str, update_data: dict) -> Optional[Document]:
        doc = self.get_by_id(entity_id)
        if not doc:
            return None
        for key, val in update_data.items():
            if val is not None:
                setattr(doc, key, val)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, entity_id: str) -> bool:
        doc = self.get_by_id(entity_id)
        if not doc:
            return False
        self.db.delete(doc)
        self.db.commit()
        return True
