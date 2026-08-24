"""add indexes and constraints

Revision ID: be30a5f33a44
Revises: 89b0bede755a
Create Date: 2026-08-24 23:20:02.659054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be30a5f33a44'
down_revision: Union[str, Sequence[str], None] = '89b0bede755a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
