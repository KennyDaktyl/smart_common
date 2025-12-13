"""auto migration 2025-12-13T11:12:54+00:00

Revision ID: ae9303157078
Revises: 93fe87d39d48
Create Date: 2025-12-13 12:12:54.754505
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ae9303157078'
down_revision = '93fe87d39d48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Define upgrade migrations."""
    pass


def downgrade() -> None:
    """Define downgrade migrations."""
    pass
