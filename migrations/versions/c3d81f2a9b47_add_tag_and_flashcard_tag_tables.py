"""add tag and flashcard_tag tables

Revision ID: c3d81f2a9b47
Revises: be30a5f33a44
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d81f2a9b47'
down_revision: Union[str, Sequence[str], None] = 'be30a5f33a44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tag',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tag_key', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tag_tag_key'), 'tag', ['tag_key'], unique=True)
    op.create_index(op.f('ix_tag_label'), 'tag', ['label'], unique=False)
    op.create_index(op.f('ix_tag_category'), 'tag', ['category'], unique=False)
    op.create_table(
        'flashcard_tag',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('flashcard_id', sa.String(), nullable=False),
        sa.Column('tag_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flashcard_id', 'tag_id'),
    )
    op.create_index(op.f('ix_flashcard_tag_flashcard_id'), 'flashcard_tag', ['flashcard_id'], unique=False)
    op.create_index(op.f('ix_flashcard_tag_tag_id'), 'flashcard_tag', ['tag_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_flashcard_tag_tag_id'), table_name='flashcard_tag')
    op.drop_index(op.f('ix_flashcard_tag_flashcard_id'), table_name='flashcard_tag')
    op.drop_table('flashcard_tag')
    op.drop_index(op.f('ix_tag_category'), table_name='tag')
    op.drop_index(op.f('ix_tag_label'), table_name='tag')
    op.drop_index(op.f('ix_tag_tag_key'), table_name='tag')
    op.drop_table('tag')
