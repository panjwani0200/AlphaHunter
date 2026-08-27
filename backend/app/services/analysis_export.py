from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.core.config import PROJECT_ROOT
from app.domain.contracts import ScannerCandidate


@dataclass(frozen=True)
class AnalysisExportResult:
    file_path: Path
    generated_at: datetime
    row_count: int


class AnalysisExportService:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or (PROJECT_ROOT / "data" / "exports" / "analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def latest_file(self) -> Path | None:
        latest_copy = self.output_dir / "alpha_hunter_latest_analysis.csv"
        if latest_copy.exists():
            return latest_copy

        timestamped = sorted(self.output_dir.glob("alpha_hunter_analysis_*.csv"))
        return timestamped[-1] if timestamped else None

    def list_exports(self) -> list[Path]:
        return sorted(
            [
                path
                for path in self.output_dir.glob("alpha_hunter_analysis_*.csv")
                if path.name != "alpha_hunter_latest_analysis.csv"
            ],
            reverse=True,
        )

    def export_candidates(
        self,
        candidates: Sequence[ScannerCandidate],
        generated_at: datetime | None = None,
    ) -> AnalysisExportResult:
        timestamp = generated_at or datetime.now(timezone.utc)
        timestamp_label = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        file_path = self.output_dir / f"alpha_hunter_analysis_{timestamp_label}.csv"
        latest_copy = self.output_dir / "alpha_hunter_latest_analysis.csv"

        rows = [self._candidate_row(candidate, timestamp) for candidate in candidates]
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._fieldnames())
            writer.writeheader()
            writer.writerows(rows)

        shutil.copyfile(file_path, latest_copy)

        return AnalysisExportResult(file_path=latest_copy, generated_at=timestamp, row_count=len(rows))

    def _fieldnames(self) -> list[str]:
        return [
            "generated_at",
            "analysis_type",
            "symbol",
            "rank",
            "signal_type",
            "score",
            "price_breakout_score",
            "oi_score",
            "volume_score",
            "futures_premium_score",
            "rsi_score",
            "option_chain_score",
            "sector_strength_score",
            "sector",
            "last_price",
            "previous_close",
            "change_percent",
            "volume",
            "average_volume_20d",
            "delivery_percent",
            "trend",
            "support",
            "resistance",
            "rsi_14",
            "breakout_quality",
            "oi_interpretation",
            "oi_change_percent",
            "open_interest",
            "pcr",
            "option_support",
            "option_resistance",
            "reasons",
            "conflicts",
            "ai_summary",
        ]

    def _candidate_row(
        self,
        candidate: ScannerCandidate,
        generated_at: datetime,
    ) -> dict[str, str | int | float | None]:
        evidence = candidate.evidence or {}
        return {
            "generated_at": generated_at.isoformat(),
            "analysis_type": "scanner",
            "symbol": candidate.symbol,
            "rank": candidate.rank,
            "signal_type": candidate.signal_type.value,
            "score": candidate.score,
            "price_breakout_score": candidate.price_breakout_score,
            "oi_score": candidate.oi_score,
            "volume_score": candidate.volume_score,
            "futures_premium_score": candidate.futures_premium_score,
            "rsi_score": candidate.rsi_score,
            "option_chain_score": candidate.option_chain_score,
            "sector_strength_score": candidate.sector_strength_score,
            "sector": self._stringify(evidence.get("sector")),
            "last_price": evidence.get("last_price"),
            "previous_close": evidence.get("previous_close"),
            "change_percent": evidence.get("change_percent"),
            "volume": evidence.get("volume"),
            "average_volume_20d": evidence.get("average_volume_20d"),
            "delivery_percent": evidence.get("delivery_percent"),
            "trend": self._stringify(evidence.get("trend")),
            "support": evidence.get("support"),
            "resistance": evidence.get("resistance"),
            "rsi_14": evidence.get("rsi_14"),
            "breakout_quality": evidence.get("breakout_quality"),
            "oi_interpretation": self._stringify(evidence.get("oi_interpretation")),
            "oi_change_percent": evidence.get("oi_change_percent"),
            "open_interest": evidence.get("open_interest"),
            "pcr": evidence.get("pcr"),
            "option_support": evidence.get("option_support"),
            "option_resistance": evidence.get("option_resistance"),
            "reasons": self._join(candidate.reasons),
            "conflicts": self._join(candidate.conflicts),
            "ai_summary": self._stringify(evidence.get("ai_summary")),
        }

    def _join(self, values: Sequence[str]) -> str:
        return " | ".join(values)

    def _stringify(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (str, int, float)):
            return str(value)
        return json.dumps(value, ensure_ascii=False)

