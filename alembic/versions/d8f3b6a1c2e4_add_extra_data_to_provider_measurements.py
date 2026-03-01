"""add extra_data to provider_measurements

Revision ID: d8f3b6a1c2e4
Revises: 2f0f1b731a6b
Create Date: 2026-03-01 15:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8f3b6a1c2e4"
down_revision: Union[str, Sequence[str], None] = "2f0f1b731a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "provider_measurements",
        sa.Column(
            "extra_data",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.alter_column(
        "provider_measurements",
        "extra_data",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("provider_measurements", "extra_data")
