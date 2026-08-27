from app.domain.contracts import PositionInput
from app.services.analysis_export import AnalysisExportService
from app.services.trading_service import TradingService


def test_scanner_returns_ranked_candidates() -> None:
    service = TradingService()

    candidates = service.run_scan(limit=5)

    assert candidates
    assert candidates[0].rank == 1
    assert candidates[0].score >= candidates[-1].score
    assert candidates[0].evidence["ai_summary"]


def test_scanner_exports_timestamped_csv(tmp_path) -> None:
    service = TradingService()
    service.exporter = AnalysisExportService(output_dir=tmp_path)

    candidates = service.run_scan(limit=4)
    latest_export = service.latest_analysis_export()

    assert candidates
    assert latest_export is not None
    assert latest_export.exists()
    assert len(service.list_analysis_exports()) == 1

    csv_text = latest_export.read_text(encoding="utf-8")
    assert "symbol,rank,signal_type" in csv_text
    assert candidates[0].symbol in csv_text


def test_position_guardian_scores_positions() -> None:
    service = TradingService()

    position = service.add_position(PositionInput(symbol="ADANIPOWER", entry_price=225, quantity=1))

    assert position.health_score is not None
    assert position.reversal_score is not None
    assert position.action.value in {"hold", "watch", "reduce", "exit"}


def test_backtest_returns_metrics() -> None:
    service = TradingService()

    metrics = service.backtest()

    assert metrics.trades >= 0
    assert 0 <= metrics.win_rate <= 100
    assert 0 <= metrics.precision <= 100
