"""Add security archive records.

Revision ID: 20260625_0002
Revises: 20260623_0001
Create Date: 2026-06-25 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260625_0002"
down_revision: Union[str, None] = "20260623_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_archive_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("series", sa.String(length=8), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("previous_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("open_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("high_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("low_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("last_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("vwap", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_traded_quantity", sa.BigInteger(), nullable=True),
        sa.Column("turnover", sa.Numeric(24, 2), nullable=True),
        sa.Column("number_of_trades", sa.BigInteger(), nullable=True),
        sa.Column("deliverable_quantity", sa.BigInteger(), nullable=True),
        sa.Column("delivery_to_traded_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "series",
            "trade_date",
            "source",
            name="uq_security_archive_symbol_series_date_source",
        ),
    )
    op.create_index(
        "ix_security_archive_symbol_date",
        "security_archive_records",
        ["symbol", "trade_date"],
    )
    op.create_index(
        "ix_security_archive_date_delivery",
        "security_archive_records",
        ["trade_date", "delivery_to_traded_percent"],
    )
    op.create_index(
        "ix_security_archive_trade_date_brin",
        "security_archive_records",
        ["trade_date"],
        postgresql_using="brin",
    )
    op.execute(
        """
        CREATE TRIGGER trg_security_archive_records_updated_at
        BEFORE UPDATE ON security_archive_records
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_security_archive_records_updated_at ON security_archive_records;"
    )
    op.drop_index("ix_security_archive_trade_date_brin", table_name="security_archive_records")
    op.drop_index("ix_security_archive_date_delivery", table_name="security_archive_records")
    op.drop_index("ix_security_archive_symbol_date", table_name="security_archive_records")
    op.drop_table("security_archive_records")

