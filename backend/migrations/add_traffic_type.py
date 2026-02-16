"""
Database Migration: Add traffic_type and tunnel_id to TrafficLog

This migration adds support for separating direct and tunnel traffic.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_traffic_type'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add traffic_type and tunnel_id columns to traffic_logs table"""
    
    # Create enum type for traffic_type
    traffic_type_enum = postgresql.ENUM('direct', 'tunnel', name='traffictype')
    traffic_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add traffic_type column with default 'direct'
    op.add_column('traffic_logs',
        sa.Column('traffic_type', 
                  sa.Enum('direct', 'tunnel', name='traffictype'),
                  nullable=False,
                  server_default='direct')
    )
    
    # Add tunnel_id column (nullable, for tunnel traffic only)
    op.add_column('traffic_logs',
        sa.Column('tunnel_id', sa.Integer(), nullable=True)
    )
    
    # Create index for better query performance
    op.create_index('ix_traffic_logs_traffic_type', 'traffic_logs', ['traffic_type'])
    op.create_index('ix_traffic_logs_tunnel_id', 'traffic_logs', ['tunnel_id'])


def downgrade():
    """Remove traffic_type and tunnel_id columns"""
    
    # Drop indexes
    op.drop_index('ix_traffic_logs_tunnel_id', table_name='traffic_logs')
    op.drop_index('ix_traffic_logs_traffic_type', table_name='traffic_logs')
    
    # Drop columns
    op.drop_column('traffic_logs', 'tunnel_id')
    op.drop_column('traffic_logs', 'traffic_type')
    
    # Drop enum type
    traffic_type_enum = postgresql.ENUM('direct', 'tunnel', name='traffictype')
    traffic_type_enum.drop(op.get_bind(), checkfirst=True)
