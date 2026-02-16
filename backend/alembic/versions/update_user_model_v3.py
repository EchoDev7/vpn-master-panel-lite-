"""Update user model with last_login and fix timestamps

Revision ID: update_user_model_v3
Revises: add_subscriptions
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'update_user_model_v3'
down_revision = 'add_subscriptions'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_login column to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login', sa.DateTime(), nullable=True))
    
    # Note: created_at and updated_at already exist in the users table
    # We just reorganized them in the model, no database changes needed


def downgrade():
    # Remove last_login column
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_login')
