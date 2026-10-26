"""(اختياري) جلب بيانات من PVGIS عبر pvlib. بيحتاج إنترنت. ما اتجرّبش في بيئة التطوير (بدون إنترنت)، فاختبره عندك.

الاستخدام: daily = fetch_pvgis_daily_expected(cfg, 2019, 2020)
بيرجّع الإنتاج اليومي المنمذج للنظام (كيلووات ساعة) من بيانات الأقمار الصناعية لسنوات ماضية.
ممكن تستخدمه كمتوسط مناخي (Climatology) لمقارنة يوم بنفس اليوم من السنين السابقة، لكنه مش بيعرف طقس اليوم الحالي.
"""
from __future__ import annotations
import pandas as pd
from .config import SystemConfig


def fetch_pvgis_daily_expected(cfg: SystemConfig, start_year: int, end_year: int, loss_pct: float = 14.0) -> pd.Series:
    import pvlib
    data, meta, inputs = pvlib.iotools.get_pvgis_hourly(
        cfg.lat, cfg.lon, start=start_year, end=end_year, pvcalculation=True, peakpower=cfg.kwp, loss=loss_pct,
        surface_tilt=cfg.tilt, surface_azimuth=cfg.azimuth, outputformat="json", usehorizon=True, components=False)
    kwh = (data["P"] / 1000.0).resample("D").sum()  # P بالوات لكل ساعة
    kwh.index = kwh.index.tz_localize(None).normalize()
    return kwh
