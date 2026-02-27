import logging
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.scheduler import Scheduler
from smart_common.repositories.scheduler import SchedulerRepository


class SchedulerService:
    def __init__(
        self,
        repo_factory: Callable[[Session], SchedulerRepository],
    ):
        self._repo_factory = repo_factory
        self.logger = logging.getLogger(__name__)

    def _repo(self, db: Session) -> SchedulerRepository:
        return self._repo_factory(db)

    def _ensure_scheduler(self, db: Session, user_id: int, scheduler_id: int) -> Scheduler:
        scheduler = self._repo(db).get_for_user_by_id(scheduler_id, user_id)
        if not scheduler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduler not found",
            )
        return scheduler

    def list_for_user(self, db: Session, user_id: int) -> list[Scheduler]:
        return self._repo(db).list_for_user(user_id)

    def create_scheduler(self, db: Session, user_id: int, payload: dict) -> Scheduler:
        scheduler = self._repo(db).create_for_user(
            user_id=user_id,
            name=payload["name"],
            slots=payload["slots"],
        )
        db.commit()
        db.refresh(scheduler)
        return scheduler

    def update_scheduler(
        self,
        db: Session,
        user_id: int,
        scheduler_id: int,
        payload: dict,
    ) -> Scheduler:
        scheduler = self._ensure_scheduler(db, user_id, scheduler_id)
        updated = self._repo(db).update_scheduler(
            scheduler,
            name=payload["name"],
            slots=payload["slots"],
        )
        db.commit()
        db.refresh(updated)
        return updated

    def delete_scheduler(self, db: Session, user_id: int, scheduler_id: int) -> None:
        scheduler = self._ensure_scheduler(db, user_id, scheduler_id)
        self._repo(db).delete(scheduler)
        db.commit()
