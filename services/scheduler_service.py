import logging
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.scheduler import Scheduler
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.scheduler import SchedulerRepository
from smart_common.schemas.device_dependency import (
    DeviceDependencyRule,
    parse_device_dependency_rule,
)


class SchedulerService:
    def __init__(
        self,
        repo_factory: Callable[[Session], SchedulerRepository],
        device_repo_factory: Callable[[Session], DeviceRepository] | None = None,
    ):
        self._repo_factory = repo_factory
        self._device_repo_factory = device_repo_factory
        self.logger = logging.getLogger(__name__)

    def _repo(self, db: Session) -> SchedulerRepository:
        return self._repo_factory(db)

    def _device_repo(self, db: Session) -> DeviceRepository:
        if self._device_repo_factory is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Device repository is not configured",
            )
        return self._device_repo_factory(db)

    def _ensure_scheduler(
        self, db: Session, user_id: int, scheduler_id: int
    ) -> Scheduler:
        scheduler = self._repo(db).get_for_user_by_id(scheduler_id, user_id)
        if not scheduler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduler not found",
            )
        return scheduler

    def _normalize_slot_dependency_rules(
        self,
        *,
        db: Session,
        user_id: int,
        slots: list[dict],
    ) -> list[dict]:
        normalized_slots: list[dict] = []
        for slot in slots:
            normalized_slot = dict(slot)
            dependency_rule = parse_device_dependency_rule(
                normalized_slot.get("device_dependency_rule")
            )
            if dependency_rule is None:
                normalized_slots.append(normalized_slot)
                continue

            target_device = self._device_repo(db).get_for_user_by_id(
                dependency_rule.target_device_id,
                user_id,
            )
            if target_device is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dependency target device not found",
                )

            normalized_slot["device_dependency_rule"] = DeviceDependencyRule(
                target_device_id=target_device.id,
                target_device_number=target_device.device_number,
                when_source_on=dependency_rule.when_source_on,
                when_source_off=dependency_rule.when_source_off,
            )
            normalized_slots.append(normalized_slot)

        return normalized_slots

    def list_for_user(self, db: Session, user_id: int) -> list[Scheduler]:
        return self._repo(db).list_for_user(user_id)

    def create_scheduler(self, db: Session, user_id: int, payload: dict) -> Scheduler:
        normalized_slots = self._normalize_slot_dependency_rules(
            db=db,
            user_id=user_id,
            slots=payload["slots"],
        )
        scheduler = self._repo(db).create_for_user(
            user_id=user_id,
            name=payload["name"],
            timezone_name=payload["timezone"],
            utc_offset_minutes=payload["utc_offset_minutes"],
            slots=normalized_slots,
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
        normalized_slots = self._normalize_slot_dependency_rules(
            db=db,
            user_id=user_id,
            slots=payload["slots"],
        )
        updated = self._repo(db).update_scheduler(
            scheduler,
            name=payload["name"],
            timezone_name=payload["timezone"],
            utc_offset_minutes=payload["utc_offset_minutes"],
            slots=normalized_slots,
        )
        db.commit()
        db.refresh(updated)
        return updated

    def delete_scheduler(self, db: Session, user_id: int, scheduler_id: int) -> None:
        scheduler = self._ensure_scheduler(db, user_id, scheduler_id)
        self._repo(db).delete(scheduler)
        db.commit()
