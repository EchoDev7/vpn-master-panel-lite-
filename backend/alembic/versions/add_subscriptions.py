"""Add subscription tables

Revision ID: add_subscriptions
Revises: add_notifications_activity
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = 'add_subscriptions'
down_revision = 'add_notifications_activity'
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('traffic_limit_gb', sa.Integer(), nullable=True),
        sa.Column('connection_limit', sa.Integer(), nullable=True),
        sa.Column('max_devices', sa.Integer(), nullable=True),
        sa.Column('features', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)
    
    # Create user_subscriptions table
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=True),
        sa.Column('traffic_used_gb', sa.Float(), nullable=True),
        sa.Column('traffic_limit_gb', sa.Integer(), nullable=True),
        sa.Column('connection_limit', sa.Integer(), nullable=True),
        sa.Column('payment_status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', 'CANCELLED', name='paymentstatus'), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_id', sa.String(length=255), nullable=True),
        sa.Column('amount_paid', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_subscriptions_id'), 'user_subscriptions', ['id'], unique=False)
    
    # Create subscription_history table
    op.create_table(
        'subscription_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_id', sa.String(length=255), nullable=True),
        sa.Column('payment_status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', 'CANCELLED', name='paymentstatus'), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['user_subscriptions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_history_id'), 'subscription_history', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_subscription_history_id'), table_name='subscription_history')
    op.drop_table('subscription_history')
    op.drop_index(op.f('ix_user_subscriptions_id'), table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
    op.drop_index(op.f('ix_subscription_plans_id'), table_name='subscription_plans')
    op.drop_table('subscription_plans')
