from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from smart_common.enums.scheduler import SchedulerCommandAction, SchedulerCommandStatus
from smart_common.models.scheduler_command import SchedulerCommand
from smart_common.schemas.scheduler_runtime import DispatchCommandEntry, DueSchedulerEntry


class SchedulerCommandRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue_command(
        self,
        *,
        minute_key: datetime,
        entry: DueSchedulerEntry,
        action: SchedulerCommandAction,
        trigger_reason: str | None = None,
        measured_value: float | None = None,
        measured_unit: str | None = None,
        now_utc: datetime | None = None,
    ) -> bool:
        now = _utc_now() if now_utc is None else now_utc
        stmt = (
            insert(SchedulerCommand)
            .values(
                command_id=uuid4(),
                minute_key=minute_key,
                device_id=entry.device_id,
                device_uuid=entry.device_uuid,
                device_number=entry.device_number,
                microcontroller_uuid=entry.microcontroller_uuid,
                scheduler_id=entry.scheduler_id,
                slot_id=entry.slot_id,
                user_id=entry.user_id,
                action=action,
                status=SchedulerCommandStatus.PENDING,
                attempt=0,
                next_retry_at=now,
                trigger_reason=trigger_reason,
                measured_value=measured_value,
                measured_unit=measured_unit,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_scheduler_idempotency")
        )
        result = self.db.execute(stmt)
        return bool(result.rowcount)

    def claim_pending_for_dispatch(
        self,
        *,
        limit: int,
        now_utc: datetime,
        ack_timeout_sec: float,
        max_inflight_per_microcontroller: int,
    ) -> list[DispatchCommandEntry]:
        limited = max(1, limit)
        inflight_limit = max(1, max_inflight_per_microcontroller)
        ack_timeout = max(1.0, ack_timeout_sec)

        # NOTE:
        # PostgreSQL does not allow FOR UPDATE with GROUP BY in the same query.
        # We lock only pending rows first, then apply per-microcontroller inflight
        # filtering in-memory using a separate aggregate query.
        candidate_limit = max(limited * 4, limited)
        lock_stmt: Select = (
            select(SchedulerCommand)
            .where(
                SchedulerCommand.status == SchedulerCommandStatus.PENDING,
                or_(
                    SchedulerCommand.next_retry_at.is_(None),
                    SchedulerCommand.next_retry_at <= now_utc,
                ),
            )
            .order_by(SchedulerCommand.minute_key.asc(), SchedulerCommand.id.asc())
            .limit(candidate_limit)
            .with_for_update(skip_locked=True)
        )
        candidates = list(self.db.execute(lock_stmt).scalars().all())
        if not candidates:
            return []

        microcontroller_ids = {item.microcontroller_uuid for item in candidates}
        inflight_counts: dict[UUID, int] = {}
        if microcontroller_ids:
            inflight_rows = self.db.execute(
                select(
                    SchedulerCommand.microcontroller_uuid,
                    func.count(SchedulerCommand.id),
                )
                .where(
                    SchedulerCommand.status == SchedulerCommandStatus.SENT,
                    SchedulerCommand.microcontroller_uuid.in_(microcontroller_ids),
                )
                .group_by(SchedulerCommand.microcontroller_uuid)
            ).all()
            inflight_counts = {
                row[0]: int(row[1])
                for row in inflight_rows
            }

        ack_deadline = now_utc + timedelta(seconds=ack_timeout)
        chosen_per_micro: dict[UUID, int] = {}
        commands: list[SchedulerCommand] = []
        for candidate in candidates:
            current_sent = inflight_counts.get(candidate.microcontroller_uuid, 0)
            already_chosen = chosen_per_micro.get(candidate.microcontroller_uuid, 0)
            if current_sent + already_chosen >= inflight_limit:
                continue
            commands.append(candidate)
            chosen_per_micro[candidate.microcontroller_uuid] = already_chosen + 1
            if len(commands) >= limited:
                break

        if not commands:
            return []

        result: list[DispatchCommandEntry] = []
        for command in commands:
            command.status = SchedulerCommandStatus.SENT
            command.ack_deadline_at = ack_deadline
            command.updated_at = now_utc
            result.append(_to_dispatch_entry(command))
        return result

    def mark_publish_failure(
        self,
        *,
        command_id: UUID,
        now_utc: datetime,
        max_retry: int,
        retry_backoff_sec: float,
        retry_jitter_sec: float,
    ) -> SchedulerCommand | None:
        command = self._get_for_update(command_id=command_id)
        if command is None:
            return None
        if command.status in _FINAL_STATUSES:
            return command

        attempt = command.attempt + 1
        command.attempt = attempt
        command.updated_at = now_utc

        if attempt <= max(0, max_retry):
            backoff = max(0.0, retry_backoff_sec)
            jitter = max(0.0, retry_jitter_sec)
            delay = backoff + random.uniform(0.0, jitter)
            command.status = SchedulerCommandStatus.PENDING
            command.next_retry_at = now_utc + timedelta(seconds=delay)
            command.ack_deadline_at = None
            return command

        command.status = SchedulerCommandStatus.ACK_FAIL
        command.next_retry_at = None
        command.ack_deadline_at = None
        return command

    def mark_ack(
        self,
        *,
        command_id: UUID,
        transport_ok: bool,
        actual_state: bool | None,
        now_utc: datetime,
    ) -> tuple[SchedulerCommand | None, bool]:
        command = self._get_for_update(command_id=command_id)
        if command is None:
            return None, False
        if command.status in _FINAL_STATUSES:
            return command, False

        ack_ok = transport_ok and _state_matches(command.action, actual_state)
        command.status = (
            SchedulerCommandStatus.ACK_OK
            if ack_ok
            else SchedulerCommandStatus.ACK_FAIL
        )
        command.updated_at = now_utc
        command.next_retry_at = None
        command.ack_deadline_at = None
        return command, True

    def claim_timeouts(
        self,
        *,
        now_utc: datetime,
        limit: int,
    ) -> list[SchedulerCommand]:
        stmt = (
            select(SchedulerCommand)
            .where(
                SchedulerCommand.status == SchedulerCommandStatus.SENT,
                SchedulerCommand.ack_deadline_at.is_not(None),
                SchedulerCommand.ack_deadline_at < now_utc,
            )
            .order_by(SchedulerCommand.ack_deadline_at.asc(), SchedulerCommand.id.asc())
            .limit(max(1, limit))
            .with_for_update(skip_locked=True)
        )
        commands = list(self.db.execute(stmt).scalars().all())
        for command in commands:
            command.status = SchedulerCommandStatus.TIMEOUT
            command.updated_at = now_utc
            command.next_retry_at = None
            command.ack_deadline_at = None
        return commands

    def _get_for_update(self, *, command_id: UUID) -> SchedulerCommand | None:
        stmt = (
            select(SchedulerCommand)
            .where(SchedulerCommand.command_id == command_id)
            .with_for_update()
        )
        return self.db.execute(stmt).scalars().first()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dispatch_entry(command: SchedulerCommand) -> DispatchCommandEntry:
    return DispatchCommandEntry(
        id=command.id,
        command_id=command.command_id,
        device_id=command.device_id,
        device_uuid=command.device_uuid,
        device_number=command.device_number,
        microcontroller_uuid=command.microcontroller_uuid,
        slot_id=command.slot_id,
        scheduler_id=command.scheduler_id,
        user_id=command.user_id,
        action=command.action,
    )


_FINAL_STATUSES = {
    SchedulerCommandStatus.ACK_OK,
    SchedulerCommandStatus.ACK_FAIL,
    SchedulerCommandStatus.TIMEOUT,
    SchedulerCommandStatus.CANCELLED,
}


def _state_matches(action: SchedulerCommandAction, actual_state: bool | None) -> bool:
    if actual_state is None:
        return False
    if action == SchedulerCommandAction.ON:
        return actual_state is True
    return actual_state is False
