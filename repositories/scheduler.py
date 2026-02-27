from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import selectinload

from smart_common.models.scheduler import Scheduler
from smart_common.models.scheduler_slot import SchedulerSlot
from smart_common.repositories.base import BaseRepository


class SchedulerRepository(BaseRepository[Scheduler]):
    model = Scheduler
    default_order_by = Scheduler.created_at.desc()

    def list_for_user(self, user_id: int) -> list[Scheduler]:
        return (
            self.session.query(self.model)
            .options(selectinload(self.model.slots))
            .filter(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_for_user_by_id(self, scheduler_id: int, user_id: int) -> Scheduler | None:
        return (
            self.session.query(self.model)
            .options(selectinload(self.model.slots))
            .filter(
                self.model.id == scheduler_id,
                self.model.user_id == user_id,
            )
            .first()
        )

    def create_for_user(
        self,
        *,
        user_id: int,
        name: str,
        slots: list[dict],
    ) -> Scheduler:
        scheduler = Scheduler(
            user_id=user_id,
            name=name,
            slots=[SchedulerSlot(**slot) for slot in slots],
        )
        self.session.add(scheduler)
        self.session.flush()
        self.session.refresh(scheduler)
        return scheduler

    def update_scheduler(
        self,
        scheduler: Scheduler,
        *,
        name: str,
        slots: list[dict],
    ) -> Scheduler:
        scheduler.name = name
        scheduler.updated_at = datetime.now(timezone.utc)
        scheduler.slots.clear()
        scheduler.slots.extend(SchedulerSlot(**slot) for slot in slots)
        self.session.flush()
        self.session.refresh(scheduler)
        return scheduler
