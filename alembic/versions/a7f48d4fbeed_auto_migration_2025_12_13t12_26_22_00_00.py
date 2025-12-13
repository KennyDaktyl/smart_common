"""auto migration 2025-12-13T12:26:22+00:00

Revision ID: a7f48d4fbeed
Revises: ae9303157078
Create Date: 2025-12-13 13:26:22.409006
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7f48d4fbeed'
down_revision = 'ae9303157078'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Define upgrade migrations."""
    pass


def downgrade() -> None:
    """Define downgrade migrations."""
    pass
