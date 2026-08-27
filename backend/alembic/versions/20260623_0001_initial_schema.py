"""Initial database schema.

Revision ID: 20260623_0001
Revises:
Create Date: 2026-06-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260623_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMP_TABLES = [
    "stocks",
    "market_snapshots",
    "sector_strength",
    "option_chain_snapshots",
    "oi_snapshots",
    "positions",
    "trade_history",
    "alerts",
    "scanner_results",
    "fii_data",
]


def enum_type(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def create_updated_at_triggers() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table_name in TIMESTAMP_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    op.create_table(
        "stocks",
        uuid_pk(),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("nse_symbol", sa.String(length=64), nullable=True),
        sa.Column("isin", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "instrument_type",
            enum_type("contract_type", "equity", "future", "option", "index"),
            nullable=False,
        ),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=True),
        sa.Column("lot_size", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tick_size", sa.Numeric(12, 4), nullable=True),
        sa.Column("is_fno", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isin"),
        sa.UniqueConstraint("nse_symbol"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_stocks_symbol", "stocks", ["symbol"])
    op.create_index("ix_stocks_sector_active", "stocks", ["sector", "is_active"])
    op.create_index("ix_stocks_instrument_type_active", "stocks", ["instrument_type", "is_active"])

    op.create_table(
        "market_snapshots",
        uuid_pk(),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), server_default="1d", nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("open_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("high_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("low_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("last_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("vwap", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("gap_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("average_volume_20d", sa.BigInteger(), nullable=True),
        sa.Column("delivery_quantity", sa.BigInteger(), nullable=True),
        sa.Column("delivery_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("turnover", sa.Numeric(20, 2), nullable=True),
        sa.Column("atr_14", sa.Numeric(18, 4), nullable=True),
        sa.Column("indicators", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_id",
            "timeframe",
            "observed_at",
            "source",
            name="uq_market_snapshots_stock_timeframe_observed_source",
        ),
    )
    op.create_index("ix_market_snapshots_stock_observed", "market_snapshots", ["stock_id", "observed_at"])
    op.create_index("ix_market_snapshots_symbol_observed", "market_snapshots", ["symbol", "observed_at"])
    op.create_index(
        "ix_market_snapshots_observed_at_brin",
        "market_snapshots",
        ["observed_at"],
        postgresql_using="brin",
    )

    op.create_table(
        "sector_strength",
        uuid_pk(),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "trend",
            enum_type("trend_direction", "strong_up", "up", "sideways", "down", "strong_down"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("relative_strength", sa.Numeric(9, 4), nullable=True),
        sa.Column("advance_count", sa.Integer(), nullable=True),
        sa.Column("decline_count", sa.Integer(), nullable=True),
        sa.Column("unchanged_count", sa.Integer(), nullable=True),
        sa.Column("volume_ratio", sa.Numeric(9, 4), nullable=True),
        sa.Column("leadership_symbols", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sector",
            "observed_at",
            "source",
            name="uq_sector_strength_sector_observed_source",
        ),
    )
    op.create_index("ix_sector_strength_observed_score", "sector_strength", ["observed_at", "score"])
    op.create_index("ix_sector_strength_sector_observed", "sector_strength", ["sector", "observed_at"])

    op.create_table(
        "option_chain_snapshots",
        uuid_pk(),
        sa.Column("underlying_stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("underlying_symbol", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("strike_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("option_type", enum_type("option_type", "CE", "PE"), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("last_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("bid_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("ask_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("open_interest", sa.BigInteger(), nullable=True),
        sa.Column("change_in_open_interest", sa.BigInteger(), nullable=True),
        sa.Column("implied_volatility", sa.Numeric(9, 4), nullable=True),
        sa.Column("delta", sa.Numeric(9, 6), nullable=True),
        sa.Column("gamma", sa.Numeric(9, 6), nullable=True),
        sa.Column("theta", sa.Numeric(9, 6), nullable=True),
        sa.Column("vega", sa.Numeric(9, 6), nullable=True),
        sa.Column("chain_metrics", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["underlying_stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "underlying_symbol",
            "observed_at",
            "expiry_date",
            "strike_price",
            "option_type",
            "source",
            name="uq_option_chain_contract_observed_source",
        ),
    )
    op.create_index(
        "ix_option_chain_underlying_expiry_observed",
        "option_chain_snapshots",
        ["underlying_symbol", "expiry_date", "observed_at"],
    )
    op.create_index(
        "ix_option_chain_observed_at_brin",
        "option_chain_snapshots",
        ["observed_at"],
        postgresql_using="brin",
    )
    op.create_index(
        "ix_option_chain_oi",
        "option_chain_snapshots",
        ["underlying_symbol", "expiry_date", "option_type", "open_interest"],
    )

    op.create_table(
        "oi_snapshots",
        uuid_pk(),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("contract_symbol", sa.String(length=96), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "contract_type",
            enum_type("contract_type", "equity", "future", "option", "index"),
            nullable=False,
        ),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("strike_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("option_type", enum_type("option_type", "CE", "PE"), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("underlying_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("contract_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("futures_premium", sa.Numeric(18, 4), nullable=True),
        sa.Column("open_interest", sa.BigInteger(), nullable=True),
        sa.Column("change_in_open_interest", sa.BigInteger(), nullable=True),
        sa.Column("oi_change_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column(
            "interpretation",
            enum_type(
                "oi_interpretation",
                "long_buildup",
                "long_unwinding",
                "short_buildup",
                "short_covering",
                "neutral",
            ),
            nullable=True,
        ),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "observed_at",
            "contract_type",
            "expiry_date",
            "strike_price",
            "option_type",
            "source",
            name="uq_oi_snapshots_contract_observed_source",
        ),
    )
    op.create_index("ix_oi_snapshots_stock_observed", "oi_snapshots", ["stock_id", "observed_at"])
    op.create_index("ix_oi_snapshots_symbol_observed", "oi_snapshots", ["symbol", "observed_at"])
    op.create_index("ix_oi_snapshots_interpretation_observed", "oi_snapshots", ["interpretation", "observed_at"])
    op.create_index(
        "ix_oi_snapshots_observed_at_brin",
        "oi_snapshots",
        ["observed_at"],
        postgresql_using="brin",
    )

    op.create_table(
        "positions",
        uuid_pk(),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column(
            "instrument_type",
            enum_type("contract_type", "equity", "future", "option", "index"),
            nullable=False,
        ),
        sa.Column("side", enum_type("position_side", "long", "short"), nullable=False),
        sa.Column(
            "status",
            enum_type("position_status", "open", "closed", "cancelled"),
            server_default="open",
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("stop_loss", sa.Numeric(18, 4), nullable=True),
        sa.Column("target_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("option_type", enum_type("option_type", "CE", "PE"), nullable=True),
        sa.Column("strike_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_health_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("latest_reversal_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_positions_status_symbol", "positions", ["status", "symbol"])
    op.create_index("ix_positions_symbol_opened", "positions", ["symbol", "opened_at"])
    op.create_index("ix_positions_expiry_status", "positions", ["expiry_date", "status"])

    op.create_table(
        "trade_history",
        uuid_pk(),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("setup_type", sa.String(length=80), nullable=False),
        sa.Column(
            "instrument_type",
            enum_type("contract_type", "equity", "future", "option", "index"),
            nullable=False,
        ),
        sa.Column("side", enum_type("position_side", "long", "short"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("pnl_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("pnl_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("result", enum_type("trade_result", "win", "loss", "breakeven"), nullable=True),
        sa.Column("max_favorable_excursion", sa.Numeric(18, 4), nullable=True),
        sa.Column("max_adverse_excursion", sa.Numeric(18, 4), nullable=True),
        sa.Column("entry_reason", sa.Text(), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("lessons", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_history_symbol_entry", "trade_history", ["symbol", "entry_time"])
    op.create_index("ix_trade_history_setup_result", "trade_history", ["setup_type", "result"])
    op.create_index("ix_trade_history_position", "trade_history", ["position_id"])

    op.create_table(
        "alerts",
        uuid_pk(),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column(
            "alert_type",
            enum_type(
                "alert_type",
                "swing_entry",
                "breakout",
                "reversal",
                "long_buildup",
                "short_buildup",
                "sector_rotation",
                "institutional_flow",
                "portfolio_summary",
                "daily_report",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            enum_type("alert_severity", "info", "warning", "reduce", "exit", "critical"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum_type("alert_status", "pending", "sent", "failed", "acknowledged", "suppressed"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(6, 2), nullable=True),
        sa.Column("channel", sa.String(length=40), server_default="telegram", nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )
    op.create_index("ix_alerts_type_status_triggered", "alerts", ["alert_type", "status", "triggered_at"])
    op.create_index("ix_alerts_symbol_triggered", "alerts", ["symbol", "triggered_at"])
    op.create_index("ix_alerts_triggered_at_brin", "alerts", ["triggered_at"], postgresql_using="brin")

    op.create_table(
        "scanner_results",
        uuid_pk(),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scanner_type", sa.String(length=80), nullable=False),
        sa.Column(
            "signal_type",
            enum_type("scanner_signal_type", "swing_long", "swing_short", "breakout", "momentum", "reversal"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("price_breakout_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("oi_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("volume_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("futures_premium_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("rsi_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("option_chain_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("sector_strength_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("conflicts", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scan_run_id",
            "scanner_type",
            "symbol",
            "signal_type",
            name="uq_scanner_results_run_type_symbol_signal",
        ),
    )
    op.create_index("ix_scanner_results_run_rank", "scanner_results", ["scan_run_id", "rank"])
    op.create_index(
        "ix_scanner_results_observed_signal_score",
        "scanner_results",
        ["observed_at", "signal_type", "score"],
    )
    op.create_index("ix_scanner_results_symbol_observed", "scanner_results", ["symbol", "observed_at"])

    op.create_table(
        "fii_data",
        uuid_pk(),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("investor_type", enum_type("investor_type", "fii", "dii"), nullable=False),
        sa.Column(
            "market_segment",
            enum_type(
                "market_segment",
                "cash",
                "index_futures",
                "index_options",
                "stock_futures",
                "stock_options",
            ),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("buy_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("sell_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("buy_contracts", sa.BigInteger(), nullable=True),
        sa.Column("sell_contracts", sa.BigInteger(), nullable=True),
        sa.Column("net_contracts", sa.BigInteger(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "observed_date",
            "investor_type",
            "market_segment",
            "source",
            name="uq_fii_data_date_investor_segment_source",
        ),
    )
    op.create_index(
        "ix_fii_data_observed_investor_segment",
        "fii_data",
        ["observed_date", "investor_type", "market_segment"],
    )

    create_updated_at_triggers()


def downgrade() -> None:
    for table_name in reversed(TIMESTAMP_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON {table_name};")

    op.drop_table("fii_data")
    op.drop_table("scanner_results")
    op.drop_table("alerts")
    op.drop_table("trade_history")
    op.drop_table("positions")
    op.drop_table("oi_snapshots")
    op.drop_table("option_chain_snapshots")
    op.drop_table("sector_strength")
    op.drop_table("market_snapshots")
    op.drop_table("stocks")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
