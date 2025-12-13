from __future__ import annotations

from typing import Generic, Iterable, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):

    model: Type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, item_id: int) -> ModelT | None:
        return self.session.get(self.model, item_id)

    def get_by_uuid(self, uuid: str) -> ModelT | None:
        return (
            self.session.query(self.model)
            .filter_by(uuid=uuid)
            .one_or_none()
        )

    def list(self) -> list[ModelT]:
        return self.session.query(self.model).all()

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
