from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.models.category import Category
from backend.models.document import Document
from backend.repositories.base import BaseRepository

DEFAULT_CATEGORIES_DATA = [
    {"name": "Academic", "description": "Course materials, syllabi, study guides and lecture notes.", "color": "#3b82f6", "icon": "book", "is_default": True},
    {"name": "Research", "description": "Academic papers, scholarly journals, survey data and abstracts.", "color": "#8b5cf6", "icon": "cpu", "is_default": True},
    {"name": "Personal", "description": "Identity records, certificates, personal taxes and resumes.", "color": "#10b981", "icon": "user", "is_default": True},
    {"name": "Projects", "description": "Software blueprints, specifications, project plans and diagrams.", "color": "#f59e0b", "icon": "briefcase", "is_default": True},
    {"name": "Business", "description": "Corporate contracts, financial invoices, purchase orders and agreements.", "color": "#ec4899", "icon": "trending-up", "is_default": True},
    {"name": "Other", "description": "Miscellaneous uncategorized files and general archives.", "color": "#64748b", "icon": "folder", "is_default": True},
]


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: str) -> Optional[Category]:
        return self.get_by_id(entity_id)

    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[Category]:
        return self.get_all(skip=skip, limit=limit)

    def get_by_id(self, entity_id: str) -> Optional[Category]:
        return self.db.execute(select(Category).where(Category.id == entity_id)).scalar_one_or_none()

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.execute(select(Category).where(func.lower(Category.name) == name.lower())).scalar_one_or_none()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Category]:
        return list(self.db.execute(select(Category).order_by(Category.name.asc()).offset(skip).limit(limit)).scalars().all())

    def get_all_with_counts(self, user_id: Optional[str] = None) -> List[tuple[Category, int]]:
        if user_id:
            stmt = (
                select(Category, func.count(Document.id).label("doc_count"))
                .outerjoin(Document, and_(Document.category_id == Category.id, Document.user_id == user_id))
                .group_by(Category.id)
                .order_by(Category.name.asc())
            )
        else:
            stmt = (
                select(Category, func.count(Document.id).label("doc_count"))
                .outerjoin(Document, and_(Document.category_id == Category.id, Document.user_id.is_(None)))
                .group_by(Category.id)
                .order_by(Category.name.asc())
            )
        return list(self.db.execute(stmt).all())

    def create(self, entity_data: dict) -> Category:
        category = Category(**entity_data)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, entity_id: str, update_data: dict) -> Optional[Category]:
        category = self.get_by_id(entity_id)
        if not category:
            return None
        for key, val in update_data.items():
            if val is not None:
                setattr(category, key, val)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, entity_id: str) -> bool:
        category = self.get_by_id(entity_id)
        if not category:
            return False
        self.db.delete(category)
        self.db.commit()
        return True

    def seed_defaults(self) -> None:
        """Seed default categories if none exist."""
        existing_count = self.db.execute(select(func.count(Category.id))).scalar()
        if existing_count == 0:
            for item in DEFAULT_CATEGORIES_DATA:
                cat = Category(**item)
                self.db.add(cat)
            self.db.commit()
