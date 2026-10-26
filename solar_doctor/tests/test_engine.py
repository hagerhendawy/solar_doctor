import numpy as np
import pandas as pd
import pytest
from engine.config import SystemConfig
from engine.expected import clear_sky_daily_kwh
from engine.synth import Scenario, make_scenario
from engine.analyze import analyze
from engine.messages import make_message

CFG = SystemConfig()


def test_clear_sky_yield_is_plausible():
    d = clear_sky_daily_kwh(CFG, pd.date_range("2026-01-01", "2026-12-31"))
    per_kwp_year = d.sum() / CFG.kwp
    assert 1700 < per_kwp_year < 2300          # سماء صافية في مصر
    assert d.min() > 8 and d.max() < 40        # نظام 6 كيلووات


def test_synthetic_generator_shapes_and_truth():
    df = make_scenario(CFG, Scenario(days=60, seed=1))
    assert len(df) == 60 and {"date", "kwh", "soiling_true"} <= set(df.columns)
    assert df.soiling_true.max() > 0.05 and (df.kwh >= 0).all()


def test_loss_estimate_close_to_truth():
    errs = []
    for seed in range(8):
        sc = Scenario(seed=seed, days=120, clean_days=(40,))
        df = make_scenario(CFG, sc)
        r = analyze(df[["date", "kwh"]], CFG, cleaning_dates=[df.date.iloc[39]])
        errs.append(abs(r["loss_pct"] - df.soiling_true.iloc[-1]))
    assert np.mean(errs) < 0.03


def test_decision_clean_now_when_cost_is_low():
    cfg = SystemConfig(clean_cost_egp=50)
    df = make_scenario(cfg, Scenario(seed=2, days=120, clean_days=(40,)))
    r = analyze(df[["date", "kwh"]], cfg, cleaning_dates=[df.date.iloc[39]])
    assert r["decision"] == "clean_now"


def test_decision_wait_when_cost_is_high():
    cfg = SystemConfig(clean_cost_egp=5000)
    df = make_scenario(cfg, Scenario(seed=2, days=120, clean_days=(40,)))
    r = analyze(df[["date", "kwh"]], cfg, cleaning_dates=[df.date.iloc[39]])
    assert r["decision"] == "wait" and r["days_until_clean"] > 20


def test_fault_is_detected_and_not_called_soiling():
    df = make_scenario(CFG, Scenario(seed=4, days=120, clean_days=(40,), fault=(110, 10, 0.35)))
    r = analyze(df[["date", "kwh"]], CFG, cleaning_dates=[df.date.iloc[39]])
    assert r["decision"] == "inspect"
    assert r["loss_pct"] < df.soiling_true.iloc[-1] + 0.05  # العطل ما اتحسبش أتربة


def test_outage_detected():
    df = make_scenario(CFG, Scenario(seed=4, days=100, clean_days=(40,), outage_days=(99, 100)))
    r = analyze(df[["date", "kwh"]], CFG, cleaning_dates=[df.date.iloc[39]])
    assert any(e["type"] == "outage" for e in r["episodes"])


def test_clean_system_is_ok():
    df = make_scenario(CFG, Scenario(seed=6, days=90, soil_rate=0.0, storm_days=(), clean_days=()))
    r = analyze(df[["date", "kwh"]], CFG)
    assert r["decision"] == "ok" and r["loss_pct"] < 0.03


def test_insufficient_data():
    df = make_scenario(CFG, Scenario(days=5))
    r = analyze(df[["date", "kwh"]], CFG)
    assert r["status"] == "insufficient_data"
    assert "7 أيام" in make_message(r)


def test_messages_arabic_for_all_decisions():
    for kw in (dict(clean_cost_egp=50), dict(clean_cost_egp=5000)):
        cfg = SystemConfig(**kw)
        df = make_scenario(cfg, Scenario(seed=2, days=120, clean_days=(40,)))
        r = analyze(df[["date", "kwh"]], cfg, cleaning_dates=[df.date.iloc[39]])
        assert "جنيه" in make_message(r)


def test_handles_missing_days_and_duplicates():
    df = make_scenario(CFG, Scenario(seed=2, days=100, clean_days=(40,)))
    df = pd.concat([df.drop(index=[10, 11, 50]), df.iloc[[20]]])
    r = analyze(df[["date", "kwh"]], CFG, cleaning_dates=[df.date.iloc[39]])
    assert r["status"] == "ok"


def test_calibration_fixes_model_mismatch_with_two_cleanings():
    from engine.analyze import calibrate_effective_tilt
    true = SystemConfig(aod700=0.25, tilt=22.0, system_loss=0.10)
    errs_raw, errs_cal = [], []
    for seed in range(6):
        df = make_scenario(CFG, Scenario(seed=seed, days=150, clean_days=(35, 85), storm_days=(20,)), true)
        cds = [df.date.iloc[34], df.date.iloc[84]]
        r0 = analyze(df[["date", "kwh"]], CFG, cleaning_dates=cds, auto_calibrate=False)
        r1 = analyze(df[["date", "kwh"]], CFG, cleaning_dates=cds)
        t = df.soiling_true.iloc[-1]
        errs_raw.append(abs(r0["loss_pct"] - t)); errs_cal.append(abs(r1["loss_pct"] - t))
        assert r1["calibration"]["calibrated"]
    assert np.mean(errs_cal) < 0.5 * np.mean(errs_raw) and np.mean(errs_cal) < 0.03


def test_calibration_skipped_with_one_cleaning():
    df = make_scenario(CFG, Scenario(seed=1, days=100, clean_days=(40,)))
    r = analyze(df[["date", "kwh"]], CFG, cleaning_dates=[df.date.iloc[39]])
    assert r["calibration"]["calibrated"] is False
