"""SQLite compatible initial migration

Revision ID: f3a80389152c
Revises: 
Create Date: 2025-01-16 04:52:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3a80389152c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('supabase_user_id', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_supabase_user_id', 'users', ['supabase_user_id'], unique=True)

    # Create bundles table
    op.create_table('bundles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('credits_images', sa.Integer(), nullable=False),
        sa.Column('credits_video', sa.Integer(), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create purchases table
    op.create_table('purchases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('stripe_payment_id', sa.String(length=255), nullable=True),
        sa.Column('amount_usd', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundles.id'])
    )
    op.create_index('ix_purchases_user_id', 'purchases', ['user_id'], unique=False)
    op.create_index('ix_purchases_stripe_payment_id', 'purchases', ['stripe_payment_id'], unique=True)
    op.create_index('ix_purchases_status', 'purchases', ['status'], unique=False)

    # Create credits table
    op.create_table('credits',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('images_remaining', sa.Integer(), nullable=False),
        sa.Column('videos_remaining', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create datasets table
    op.create_table('datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('bucket_path', sa.String(length=500), nullable=False),
        sa.Column('image_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_datasets_user_id', 'datasets', ['user_id'], unique=False)
    op.create_index('ix_datasets_bucket_path', 'datasets', ['bucket_path'], unique=False)
    op.create_index('ix_datasets_status', 'datasets', ['status'], unique=False)

    # Create lora_models table
    op.create_table('lora_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('bucket_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('steps', sa.Integer(), nullable=False),
        sa.Column('model_hash', sa.String(length=64), nullable=False),
        sa.Column('training_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE')
    )
    op.create_index('ix_lora_models_user_id', 'lora_models', ['user_id'], unique=False)
    op.create_index('ix_lora_models_dataset_id', 'lora_models', ['dataset_id'], unique=False)
    op.create_index('ix_lora_models_bucket_path', 'lora_models', ['bucket_path'], unique=False)
    op.create_index('ix_lora_models_status', 'lora_models', ['status'], unique=False)
    op.create_index('ix_lora_models_model_hash', 'lora_models', ['model_hash'], unique=True)

    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('priority', sa.SmallInteger(), nullable=False),
        sa.Column('reserved_by', sa.String(length=64), nullable=True),
        sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_jobs_user_id', 'jobs', ['user_id'], unique=False)
    op.create_index('ix_jobs_kind', 'jobs', ['kind'], unique=False)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_jobs_priority', 'jobs', ['priority'], unique=False)
    op.create_index('ix_jobs_reserved_by', 'jobs', ['reserved_by'], unique=False)

    # Create outputs table
    op.create_table('outputs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('lora_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('object_key', sa.String(length=512), nullable=False),
        sa.Column('prompt_hash', sa.String(length=32), nullable=True),
        sa.Column('seed', sa.String(length=50), nullable=True),
        sa.Column('model_hash', sa.String(length=64), nullable=True),
        sa.Column('output_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lora_id'], ['lora_models.id'], ondelete='SET NULL')
    )
    op.create_index('ix_outputs_user_id', 'outputs', ['user_id'], unique=False)
    op.create_index('ix_outputs_job_id', 'outputs', ['job_id'], unique=False)
    op.create_index('ix_outputs_lora_id', 'outputs', ['lora_id'], unique=False)
    op.create_index('ix_outputs_object_key', 'outputs', ['object_key'], unique=False)
    op.create_index('ix_outputs_prompt_hash', 'outputs', ['prompt_hash'], unique=False)
    op.create_index('ix_outputs_seed', 'outputs', ['seed'], unique=False)
    op.create_index('ix_outputs_model_hash', 'outputs', ['model_hash'], unique=False)
    op.create_index('ix_outputs_type', 'outputs', ['type'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=50), nullable=True),
        sa.Column('meta_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'], unique=False)

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(length=100), nullable=False),
        sa.Column('hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_api_keys_owner_user_id', 'api_keys', ['owner_user_id'], unique=False)
    op.create_index('ix_api_keys_scope', 'api_keys', ['scope'], unique=False)
    op.create_index('ix_api_keys_hash', 'api_keys', ['hash'], unique=True)
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'], unique=False)
    op.create_index('ix_api_keys_expires_at', 'api_keys', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_table('api_keys')
    op.drop_table('audit_logs')
    op.drop_table('outputs')
    op.drop_table('jobs')
    op.drop_table('lora_models')
    op.drop_table('datasets')
    op.drop_table('credits')
    op.drop_table('purchases')
    op.drop_table('bundles')
    op.drop_table('users')