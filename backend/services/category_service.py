from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.models.category import Category
from backend.repositories.category_repository import CategoryRepository
from backend.repositories.activity_repository import ActivityRepository
from backend.schemas.category import CategoryCreate, CategoryUpdate
from backend.utils.exceptions import EntityNotFoundException, DuplicateResourceException, AppException


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.cat_repo = CategoryRepository(db)
        self.act_repo = ActivityRepository(db)

    def get_all_with_counts(self, user_id: Optional[str] = None) -> List[Tuple[Category, int]]:
        self.cat_repo.seed_defaults()
        return self.cat_repo.get_all_with_counts(user_id=user_id)

    def get_by_id(self, category_id: str) -> Category:
        category = self.cat_repo.get_by_id(category_id)
        if not category:
            raise EntityNotFoundException(f"Category '{category_id}' not found.")
        return category

    def create_category(self, data: CategoryCreate) -> Category:
        existing = self.cat_repo.get_by_name(data.name)
        if existing:
            raise DuplicateResourceException(f"Category with name '{data.name}' already exists.")

        category = self.cat_repo.create(data.model_dump())
        self.act_repo.create({
            "activity_type": "category_create",
            "title": f"Created category '{category.name}'",
            "description": f"Created new taxonomy category '{category.name}' ({category.description or 'No description'})",
            "document_name": "-",
            "category_name": category.name,
            "status": "Success"
        })
        return category

    def update_category(self, category_id: str, data: CategoryUpdate) -> Category:
        category = self.get_by_id(category_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"] != category.name:
            existing = self.cat_repo.get_by_name(update_dict["name"])
            if existing and existing.id != category_id:
                raise DuplicateResourceException(f"Category with name '{update_dict['name']}' already exists.")

        updated = self.cat_repo.update(category_id, update_dict)
        self.act_repo.create({
            "activity_type": "category_update",
            "title": f"Updated category '{updated.name}'",
            "description": f"Updated settings and details for category '{updated.name}'",
            "document_name": "-",
            "category_name": updated.name,
            "status": "Success"
        })
        return updated

    def delete_category(self, category_id: str, reassign_to: str = "Other") -> bool:
        category = self.get_by_id(category_id)
        if category.name.lower() == "other":
            raise AppException("The default 'Other' category cannot be deleted.", status_code=400)

        # Find or create target category for reassignment
        target_name = (reassign_to or "Other").strip()
        if not target_name or target_name.lower() == category.name.lower():
            target_name = "Other"

        target_cat = self.cat_repo.get_by_name(target_name)
        if not target_cat:
            target_cat = self.cat_repo.create({
                "name": target_name,
                "description": f"Category for {target_name} documents.",
                "color": "#64748b",
                "is_default": (target_name.lower() == "other")
            })

        # Reassign documents from deleted category to target category
        reassigned_count = len(category.documents)
        for doc in category.documents:
            doc.category_id = target_cat.id
            doc.category_name = target_cat.name
        self.db.commit()

        cat_name = category.name
        deleted = self.cat_repo.delete(category_id)
        if deleted:
            self.act_repo.create({
                "activity_type": "category_delete",
                "title": f"Deleted category '{cat_name}'",
                "description": f"Deleted category '{cat_name}' ({reassigned_count} documents reassigned to '{target_cat.name}')",
                "document_name": "-",
                "category_name": target_cat.name,
                "status": "Success"
            })
        return deleted
