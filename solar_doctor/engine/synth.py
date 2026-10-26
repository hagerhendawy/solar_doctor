"""مولّد بيانات محاكاة لإنتاج نظام شمسي: أتربة، عواصف، تنظيف، مطر، أعطال، غيوم، وضوضاء قياس.

مهم: دي بيانات مصطنعة لاختبار الخوارزمية والعرض فقط. لازم تتكتب في أي عرض إنها محاكاة.
الحقيقة (soiling_true) محفوظة علشان نقيس دقة المحرك بدقة، وده شيء مش ممكن في الواقع إلا بتجربة تنظيف.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from .config import SystemConfig
from .expected import clear_sky_daily_kwh


@dataclass
class Scenario:
    start: str = "2026-08-01"
    days: int = 120
    soil_rate: float = 0.0015                # فقد الأتربة اليومي
    clean_days: tuple = (40,)                 # أيام التنظيف (رقم اليوم من البداية، يبدأ من 1)
    storm_days: tuple = (22,)                 # أيام عواصف ترابية
    storm_step: float = 0.03
    rain_days: tuple = ()
    rain_recovery: float = 0.5                # نسبة تنظيف المطر
    fault: tuple | None = None                # (يوم البداية، المدة، نسبة الفقد) مثال: (70, 8, 0.33)
    outage_days: tuple = ()
    cloud_prob: float = 0.12
    noise: float = 0.012
    bias: float = 0.97                        # فرق بين نموذجنا والنظام الحقيقي (التنظيف/الأسلاك...)
    initial_soiling: float = 0.0
    sat_noise: float = 0.04                   # خطأ بيانات السحب الصناعية لو اتستخدمت
    seed: int = 1


def make_scenario(cfg: SystemConfig, sc: Scenario, true_cfg: SystemConfig | None = None) -> pd.DataFrame:
    """true_cfg: لو متحدد، الإنتاج بيتولّد بنموذج مختلف عن اللي المحرك بيفترضه (اختبار عدم تطابق النموذج)."""
    rng = np.random.default_rng(sc.seed)
    dates = pd.date_range(sc.start, periods=sc.days, freq="D")
    ecs = clear_sky_daily_kwh(true_cfg or cfg, dates).values
    kt = np.where(rng.random(sc.days) < sc.cloud_prob, rng.uniform(0.35, 0.85, sc.days), rng.normal(0.985, 0.012, sc.days))
    kt = np.clip(kt, 0.2, 1.0)
    soil = np.zeros(sc.days); s = sc.initial_soiling
    for i in range(sc.days):
        day = i + 1
        s += sc.soil_rate * rng.uniform(0.7, 1.3)
        if day in sc.storm_days: s += sc.storm_step
        if day in sc.rain_days: s *= (1 - sc.rain_recovery)
        if day in sc.clean_days: s = 0.0
        soil[i] = s
    fault = np.zeros(sc.days)
    if sc.fault:
        d0, dur, frac = sc.fault
        fault[d0 - 1:d0 - 1 + dur] = frac
    outage = np.zeros(sc.days, bool)
    for d in sc.outage_days: outage[d - 1] = True
    actual = ecs * kt * (1 - soil) * (1 - fault) * sc.bias * (1 + rng.normal(0, sc.noise, sc.days))
    actual[outage] = rng.uniform(0, 0.3, outage.sum())
    actual = np.round(np.clip(actual, 0, None), 1)
    kt_sat = np.clip(kt * (1 + rng.normal(0, sc.sat_noise, sc.days)), 0.1, 1.05)
    return pd.DataFrame({"date": dates, "kwh": actual, "kt_sat": np.round(kt_sat, 3), "soiling_true": soil, "fault_true": fault,
                         "outage_true": outage, "kt_true": kt})


def random_scenario(seed: int, with_fault: bool | None = None, days: int = 120) -> Scenario:
    rng = np.random.default_rng(seed)
    has_fault = bool(rng.random() < 0.5) if with_fault is None else with_fault
    return Scenario(
        start="2026-08-01", days=days, soil_rate=float(rng.uniform(0.0008, 0.0025)),
        clean_days=(int(rng.integers(25, 60)),), storm_days=tuple(int(x) for x in rng.integers(10, days - 10, int(rng.integers(0, 3)))),
        storm_step=float(rng.uniform(0.02, 0.05)),
        fault=(int(rng.integers(days - 40, days - 14)), int(rng.integers(6, 12)), float(rng.uniform(0.2, 0.4))) if has_fault else None,
        bias=float(rng.uniform(0.92, 1.02)), cloud_prob=float(rng.uniform(0.05, 0.2)), noise=float(rng.uniform(0.008, 0.02)), seed=seed)
