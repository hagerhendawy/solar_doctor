"""حساب الإنتاج المتوقع اليومي في السماء الصافية (Clear-sky) بمكتبة pvlib.

ليه Clear-sky؟ لأننا ما نعتمدش على بيانات طقس لحظية. بنقارن إنتاجك الفعلي بأقصى إنتاج ممكن، وبنستخدم الأيام الصافية
(الغلاف العلوي للمنحنى) لقياس فاقد الأتربة. ولو عندك بيانات سحب (kt) من مصدر خارجي بتتحسن الدقة.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pvlib

from .config import SystemConfig


def ambient_temp_c(index: pd.DatetimeIndex) -> np.ndarray:
    """درجة حرارة هواء تقريبية لمصر (موسمية + يومية). تُستبدل ببيانات حقيقية لو متاحة."""
    doy = index.dayofyear.values
    seasonal = 22.0 + 9.0 * np.sin(2 * np.pi * (doy - 110) / 365.0)
    diurnal = 6.5 * np.sin(2 * np.pi * (index.hour.values + index.minute.values / 60.0 - 9.0) / 24.0)
    return seasonal + diurnal


def clear_sky_daily_kwh(cfg: SystemConfig, dates) -> pd.Series:
    """الإنتاج اليومي المتوقع (كيلووات ساعة) لكل تاريخ في dates بافتراض سماء صافية."""
    dates = pd.DatetimeIndex(pd.to_datetime(dates)).normalize().unique().sort_values()
    start, end = dates.min(), dates.max() + pd.Timedelta(days=1)
    idx = pd.date_range(start, end, freq="1h", tz=cfg.tz, inclusive="left") + pd.Timedelta(minutes=30)  # منتصف الساعة
    loc = pvlib.location.Location(cfg.lat, cfg.lon, tz=cfg.tz, altitude=cfg.altitude)
    sp = loc.get_solarposition(idx)
    elev = sp["apparent_elevation"]
    dni_extra = pvlib.irradiance.get_extra_radiation(idx)
    cs = pvlib.clearsky.simplified_solis(elev, aod700=cfg.aod700, precipitable_water=cfg.precipitable_water, dni_extra=dni_extra)
    cs = cs.where(elev > 0, 0.0).fillna(0.0)
    poa = pvlib.irradiance.get_total_irradiance(cfg.tilt, cfg.azimuth, sp["apparent_zenith"], sp["azimuth"],
                                                cs["dni"], cs["ghi"], cs["dhi"], dni_extra=dni_extra, model="haydavies")
    g = poa["poa_global"].clip(lower=0).fillna(0.0)
    local = idx.tz_localize(None)
    tamb = ambient_temp_c(local)
    tcell = tamb + g.values / 800.0 * (cfg.noct - 20.0)
    p_kw = cfg.kwp * g.values / 1000.0 * (1.0 + cfg.gamma * (tcell - 25.0)) * (1.0 - cfg.system_loss)
    daily = pd.Series(p_kw, index=local).resample("D").sum()  # كل نقطة = ساعة، فالمجموع = كيلووات ساعة
    daily.index = daily.index.normalize()
    return daily.reindex(dates)
