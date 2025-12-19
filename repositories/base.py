from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Type, TypeVar, Union
from sqlalchemy import UUID, String, func
from sqlalchemy.orm import Session, Query

ModelT = TypeVar("ModelT")

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):

    model: Type[ModelT]

    searchable_fields: dict[str, Any] = {}
    
    def __init__(self, session: Session) -> None:
        self.session = session
    
    def _base_query(self) -> Query:
        return self.session.query(self.model)

    def _apply_filters(
        self,
        query: Query,
        filters: dict[str, Any] | None,
    ) -> Query:
        if not filters:
            return query

        for field, value in filters.items():
            if value is None:
                continue

            column = self.searchable_fields.get(field)
            if not column:
                continue

            if isinstance(value, Enum):
                query = query.filter(column == value)

            elif isinstance(column.type, String) and isinstance(value, str):
                query = query.filter(column.ilike(f"%{value}%"))

            else:
                query = query.filter(column == value)

        return query

    def get_by_id(self, item_id: int) -> ModelT | None:
        return self.session.get(self.model, item_id)

    def get_by_uuid(self, uuid: Union[str, UUID]) -> ModelT | None:
        return self.session.query(self.model).filter_by(uuid=uuid).one_or_none()

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
    ) -> list[ModelT]:
        query = self._base_query()
        query = self._apply_filters(query, filters)

        if order_by is not None:
            query = query.order_by(order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        *,
        filters: dict[str, Any] | None = None,
    ) -> int:
        query = self.session.query(func.count("*"))
        query = query.select_from(self.model)
        query = self._apply_filters(query, filters)
        return query.scalar() or 0

    def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def partial_update(
        self,
        obj: ModelT,
        *,
        data: dict[str, Any],
        allowed_fields: set[str],
        commit: bool = True,
    ) -> ModelT:
        for field, value in data.items():
            if field in allowed_fields:
                setattr(obj, field, value)

        self.session.add(obj)

        if commit:
            self.session.commit()
            self.session.refresh(obj)

        return obj
    
    def delete(self, obj: ModelT) -> None:
        self.session.delete(obj)
        self.session.flush()
