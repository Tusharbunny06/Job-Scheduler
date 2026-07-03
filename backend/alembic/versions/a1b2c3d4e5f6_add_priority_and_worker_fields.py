"""add_priority_and_worker_fields

Revision ID: a1b2c3d4e5f6
Revises: f7c6310bd4f4
Create Date: 2026-07-02 14:00:00.000000

Adds:
- jobs.priority (Integer, default 0) — for job-level priority ordering
- workers.concurrency_limit (Integer, default 10) — tracks worker parallelism
- workers.registered_at (DateTime) — audit timestamp
- scheduled_jobs.name (String, nullable) — human-readable label
- scheduled_jobs.last_run_at (DateTime, nullable) — audit timestamp for last dispatch
- scheduled_jobs.is_active (Boolean, default True) — allow disabling without deleting
- scheduled_jobs.created_at (DateTime) — creation timestamp
- scheduled_jobs.queue_id index — for cascade performance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7c6310bd4f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add priority to jobs table
    op.add_column('jobs', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_jobs_priority', 'jobs', ['priority'], unique=False)

    # Add concurrency_limit and registered_at to workers
    op.add_column('workers', sa.Column('concurrency_limit', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('workers', sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))

    # Add name, last_run_at, is_active, created_at, and queue_id index to scheduled_jobs
    op.add_column('scheduled_jobs', sa.Column('name', sa.String(), nullable=True))
    op.add_column('scheduled_jobs', sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('scheduled_jobs', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('scheduled_jobs', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.create_index('ix_scheduled_jobs_queue_id', 'scheduled_jobs', ['queue_id'], unique=False)


def downgrade() -> None:
    # Remove scheduled_jobs additions
    op.drop_index('ix_scheduled_jobs_queue_id', table_name='scheduled_jobs')
    op.drop_column('scheduled_jobs', 'created_at')
    op.drop_column('scheduled_jobs', 'is_active')
    op.drop_column('scheduled_jobs', 'last_run_at')
    op.drop_column('scheduled_jobs', 'name')

    # Remove workers additions
    op.drop_column('workers', 'registered_at')
    op.drop_column('workers', 'concurrency_limit')

    # Remove jobs additions
    op.drop_index('ix_jobs_priority', table_name='jobs')
    op.drop_column('jobs', 'priority')
