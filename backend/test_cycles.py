from datetime import datetime, timezone
from app.domain.contracts import MarketSnapshot, TechnicalAnalysis, OiSnapshot, OiInterpretation
from app.engine.cycle_engine import detect_cycle_phase
from app.engine.signal_engine_pro import evaluate_signal_pro

def run_test():
    # Simulate Accumulation
    snap_acc = MarketSnapshot(
        symbol="TEST_ACC",
        observed_at=datetime.now(timezone.utc),
        last_price=100.0,
        previous_close=99.0,
        change_percent=1.0,
        volume=100000,
        average_volume_20d=100000,
        delivery_percent=60.0, # High delivery
        sector="IT"
    )
    tech_acc = TechnicalAnalysis(
        symbol="TEST_ACC",
        trend="neutral",
        rsi_14=50.0,
        bb_width=4.0, # Compressed volatility
        breakout_quality=2.0
    )
    oi_acc = OiSnapshot(
        symbol="TEST_ACC",
        observed_at=datetime.now(timezone.utc),
        price_change_percent=1.0,
        oi_change_percent=2.0,
        open_interest=50000,
        interpretation=OiInterpretation.NEUTRAL
    )
    
    # Simulate Markup
    snap_markup = MarketSnapshot(
        symbol="TEST_MARKUP",
        observed_at=datetime.now(timezone.utc),
        last_price=150.0,
        previous_close=140.0,
        change_percent=7.1,
        volume=250000,
        average_volume_20d=100000,
        sector="IT"
    )
    tech_markup = TechnicalAnalysis(
        symbol="TEST_MARKUP",
        trend="up",
        ema_20=145.0, # Price above EMA
        breakout_quality=9.0 # Breakout
    )
    oi_markup = OiSnapshot(
        symbol="TEST_MARKUP",
        observed_at=datetime.now(timezone.utc),
        price_change_percent=7.1,
        oi_change_percent=10.0,
        open_interest=60000,
        interpretation=OiInterpretation.LONG_BUILDUP
    )

    res_acc = detect_cycle_phase(snap_acc, tech_acc, oi_acc)
    print(f"Accumulation Test: Phase={res_acc.phase.value}, Confidence={res_acc.confidence}")
    assert res_acc.phase.value == "accumulation"

    res_markup = detect_cycle_phase(snap_markup, tech_markup, oi_markup)
    print(f"Markup Test: Phase={res_markup.phase.value}, Confidence={res_markup.confidence}")
    assert res_markup.phase.value == "markup"
    
    snap_markup.cycle_metrics = res_markup
    sig_markup = evaluate_signal_pro(snap_markup, oi_markup)
    print(f"Markup Signal Test: Final Score={sig_markup['score']}, Cycle={sig_markup['cycle']}, Reasons={sig_markup['reasons']}")
    
    print("Tests passed successfully.")

if __name__ == "__main__":
    run_test()
