"""Add notifications and activity logs tables

Revision ID: add_notifications_activity
Revises: 
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_notifications_activity'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.String(length=1000), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    
    # Create activity_logs table
    op.create_table('activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('meta_data', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_logs_id'), 'activity_logs', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_activity_logs_id'), table_name='activity_logs')
    op.drop_table('activity_logs')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
