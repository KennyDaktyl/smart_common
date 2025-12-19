"""extend user_profile fields

Revision ID: ff7d4a413a4a
Revises: b224575a2780
Create Date: 2025-12-19 10:45:04.405664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff7d4a413a4a'
down_revision: Union[str, Sequence[str], None] = 'b224575a2780'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("first_name", sa.String(100)))
    op.add_column("user_profiles", sa.Column("last_name", sa.String(100)))
    op.add_column("user_profiles", sa.Column("phone_number", sa.String(32)))
    op.add_column("user_profiles", sa.Column("company_vat", sa.String(32)))
    op.add_column("user_profiles", sa.Column("company_address", sa.String(255)))


def downgrade() -> None:
    op.drop_column("user_profiles", "company_address")
    op.drop_column("user_profiles", "company_vat")
    op.drop_column("user_profiles", "phone_number")
    op.drop_column("user_profiles", "last_name")
    op.drop_column("user_profiles", "first_name")

