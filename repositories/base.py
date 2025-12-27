from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Type, TypeVar, Union

from sqlalchemy import UUID, String, func, or_
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.sqltypes import Integer, Boolean, String

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """
    Base repository with:
    - exact filters (filters)
    - generic search (search)
    - reusable list & count
    """

    model: Type[ModelT]
    searchable_fields: dict[str, Any] = {}
    search_fields: dict[str, Any] = {}

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

            col_type = column.type

            if isinstance(value, Enum):
                query = query.filter(column == value)

            elif isinstance(col_type, Boolean) and isinstance(value, bool):
                query = query.filter(column.is_(value))

            elif isinstance(col_type, String) and isinstance(value, str):
                query = query.filter(column.ilike(f"%{value}%"))

            else:
                query = query.filter(column == value)

        return query

    def _apply_search(
        self,
        query: Query,
        *,
        search: str | None,
        search_fields: dict[str, Any],
    ) -> Query:
        if not search or not search_fields:
            return query

        conditions: list[Any] = []

        for column in search_fields.values():
            col_type = column.type

            if isinstance(col_type, Integer) and search.isdigit():
                conditions.append(column == int(search))

            elif isinstance(col_type, String):
                conditions.append(column.ilike(f"%{search}%"))

        if not conditions:
            return query

        return query.filter(or_(*conditions))

    def get_by_id(self, item_id: int) -> ModelT | None:
        return self.session.get(self.model, item_id)

    def get_by_uuid(self, uuid: Union[str, UUID]) -> ModelT | None:
        return self.session.query(self.model).filter_by(uuid=uuid).one_or_none()

    def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.session.delete(obj)
        self.session.flush()

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
        query = self.session.query(func.count("*")).select_from(self.model)
        query = self._apply_filters(query, filters)
        return query.scalar() or 0

    def list_with_search(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
        search_fields: dict[str, Any],
        order_by: Any | None = None,
        base_query: Query | None = None,
    ) -> list[ModelT]:
        query = base_query or self._base_query()

        query = self._apply_search(
            query,
            search=search,
            search_fields=search_fields,
        )

        if order_by is not None:
            query = query.order_by(order_by)

        return query.offset(offset).limit(limit).all()

    def count_with_search(
        self,
        *,
        search: str | None,
        search_fields: dict[str, Any],
        base_query: Query | None = None,
    ) -> int:
        query = base_query or self._base_query()

        query = self._apply_search(
            query,
            search=search,
            search_fields=search_fields,
        )

        return query.count()

    def partial_update(
        self,
        obj: Any,
        *,
        data: dict[str, Any],
        allowed_fields: set[str],
    ) -> Any:
        for field, value in data.items():
            if field not in allowed_fields:
                continue

            setattr(obj, field, value)

        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
