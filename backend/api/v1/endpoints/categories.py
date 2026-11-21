from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.category_service import CategoryService
from backend.api.deps import get_current_user_optional
from backend.models.user import User
from backend.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithCountResponse
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=List[CategoryWithCountResponse],
    summary="List all categories",
    description="Retrieve all taxonomy categories with live document count aggregations."
)
def list_categories(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> List[CategoryWithCountResponse]:
    service = CategoryService(db)
    user_id = current_user.id if current_user else None
    items_with_counts = service.get_all_with_counts(user_id=user_id)
    result = []
    for cat, count in items_with_counts:
        item = CategoryWithCountResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            color=cat.color,
            icon=cat.icon,
            is_default=cat.is_default,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            document_count=count
        )
        result.append(item)
    return result


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new document classification category."
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db)
) -> CategoryResponse:
    service = CategoryService(db)
    cat = service.create_category(payload)
    return CategoryResponse.model_validate(cat)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category by ID"
)
def get_category(
    category_id: str,
    db: Session = Depends(get_db)
) -> CategoryResponse:
    service = CategoryService(db)
    cat = service.get_by_id(category_id)
    return CategoryResponse.model_validate(cat)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Update metadata and properties of an existing category."
)
def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: Session = Depends(get_db)
) -> CategoryResponse:
    service = CategoryService(db)
    cat = service.update_category(category_id, payload)
    return CategoryResponse.model_validate(cat)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete category",
    description="Delete a category. Associated documents are safely reassigned to another category (defaults to 'Other')."
)
def delete_category(
    category_id: str,
    reassign_to: str = "Other",
    db: Session = Depends(get_db)
):
    service = CategoryService(db)
    service.delete_category(category_id, reassign_to=reassign_to)
    return {"success": True, "message": f"Category '{category_id}' successfully deleted and documents reassigned to '{reassign_to}'."}
