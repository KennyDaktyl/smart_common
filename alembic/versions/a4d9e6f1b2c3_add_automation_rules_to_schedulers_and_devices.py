"""add automation rules to schedulers and devices

Revision ID: a4d9e6f1b2c3
Revises: 3ac93cd18e3d, d8f3b6a1c2e4, 1c2d9f4a6b7e, c91b4d3a7e10
Create Date: 2026-03-10 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4d9e6f1b2c3"
down_revision: Union[str, Sequence[str], None] = (
    "3ac93cd18e3d",
    "d8f3b6a1c2e4",
    "1c2d9f4a6b7e",
    "c91b4d3a7e10",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "activation_rule_json",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.add_column(
        "devices",
        sa.Column(
            "auto_rule_json",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("devices", "auto_rule_json")
    op.drop_column("scheduler_slots", "activation_rule_json")
