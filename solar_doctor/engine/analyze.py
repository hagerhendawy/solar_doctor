"""محرك Solar Doctor: من قراءات الإنتاج اليومية إلى قرار (نظّف الآن / استنى / افحص عطل) بالجنيه.

الفكرة:
1) نحسب أقصى إنتاج ممكن لكل يوم (سماء صافية) بـpvlib، ونقسم الفعلي عليه => r (مؤشر أداء النظام).
2) الأيام الصافية بتكوّن "الغلاف العلوي" لـr. لو الغلاف بينزل ببطء => أتربة. لو نزل فجأة => ظل/عطل. لو طلع فجأة => تنظيف/مطر.
3) فاقد الأتربة L = 1 - الغلاف الحالي ÷ الغلاف بعد آخر تنظيف.
4) الخسارة التراكمية بالجنيه منذ آخر تنظيف تتقارن بتكلفة التنظيف. عند التعادل التنظيف أمثل (لو الفقد خطي).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .config import SystemConfig
from .expected import clear_sky_daily_kwh


def _trailing_quantile(s: pd.Series, window: int, q: float, min_periods: int = 3) -> pd.Series:
    return s.rolling(window, min_periods=min_periods).quantile(q)


def _prepare(readings: pd.DataFrame, cfg: SystemConfig) -> pd.DataFrame:
    d = readings.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    d = d.dropna(subset=["kwh"]).sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    d["kwh"] = d["kwh"].clip(lower=0)
    d["ecs"] = clear_sky_daily_kwh(cfg, d["date"]).values
    d["r"] = np.where(d["ecs"] > 3.0, d["kwh"] / d["ecs"], np.nan)
    return d


def _detect_faults(d: pd.DataFrame, r_adj: pd.Series, weather: bool) -> tuple[np.ndarray, np.ndarray, list]:
    """يرجّع (قناع أيام العطل، قناع أيام الانقطاع، قائمة حلقات الأعطال)."""
    n = len(d)
    env0 = _trailing_quantile(r_adj, 9, 0.85)
    ref = env0.shift(4).ffill()
    outage = ((d["kwh"] < 0.1 * d["ecs"]) & (d["ecs"] > 3)).values
    low = ((r_adj < 0.85 * ref) & ~pd.Series(outage)).values
    need = 3 if weather else 4
    fault = np.zeros(n, bool)
    i = 0
    episodes = []
    while i < n:
        if low[i]:
            j = i
            while j + 1 < n and low[j + 1]:
                j += 1
            if j - i + 1 >= need:
                fault[i:j + 1] = True
                sev = float(1 - np.nanmean(r_adj.values[i:j + 1] / ref.values[i:j + 1]))
                episodes.append({"start": d["date"].iloc[i], "end": d["date"].iloc[j], "days": j - i + 1, "severity": round(sev, 3), "type": "drop"})
            i = j + 1
        else:
            i += 1
    # أيام الانقطاع المتتالية
    i = 0
    while i < n:
        if outage[i]:
            j = i
            while j + 1 < n and outage[j + 1]:
                j += 1
            episodes.append({"start": d["date"].iloc[i], "end": d["date"].iloc[j], "days": j - i + 1, "severity": 1.0, "type": "outage"})
            i = j + 1
        else:
            i += 1
    return fault, outage, episodes


def _detect_recoveries(env: pd.Series, thresh: float = 0.03, lookback: int = 10, cooldown: int = 7) -> list[int]:
    """ارتفاع مفاجئ في الغلاف = تنظيف أو مطر (بدون تسجيل). بيرجّع مواضع الأيام (index)."""
    out, last = [], -999
    v = env.values
    for t in range(lookback, len(v)):
        if np.isnan(v[t]):
            continue
        prev = v[t - lookback:t]
        prev = prev[~np.isnan(prev)]
        if len(prev) < 4:
            continue
        if v[t] / np.min(prev) - 1 >= thresh and t - last > cooldown:
            out.append(t - 3)  # الغلاف بيتأخر ~3 أيام عن لحظة التنظيف الفعلية
            last = t
    return out


def analyze(readings: pd.DataFrame, cfg: SystemConfig, cleaning_dates=(), use_weather: bool | None = None,
            today=None, auto_calibrate: bool = True) -> dict:
    """readings: أعمدة date, kwh (واختياري kt_sat = مؤشر الصفاء/السحب من مصدر خارجي).
    auto_calibrate: لو فيه تنظيفتين مسجّلتين أو أكتر، بنعاير الميل الفعّال تلقائيًا (بيحسّن الدقة لما نموذج الميل/الجو مش مطابق)."""
    calib = {"calibrated": False, "reason": "تنظيفة واحدة أو أقل"}
    if auto_calibrate and len(list(cleaning_dates or ())) >= 2:
        cfg, calib = calibrate_effective_tilt(readings, cfg, cleaning_dates)
    d = _prepare(readings, cfg)
    if len(d) < 7:
        return {"status": "insufficient_data", "decision": "collect", "notes": ["محتاجين على الأقل 7 أيام قراءات."], "series": d}
    has_kt = "kt_sat" in d.columns and d["kt_sat"].notna().mean() > 0.8
    weather = has_kt if use_weather is None else bool(use_weather and has_kt)
    r_adj = d["r"] / d["kt_sat"].clip(0.3, 1.05) if weather else d["r"]
    q = 0.75 if weather else 0.85

    fault, outage, episodes = _detect_faults(d, r_adj, weather)
    bad = fault | outage
    r_use = r_adj.where(~pd.Series(bad)).copy()
    env = _trailing_quantile(r_use, 7, q).ffill(limit=10)
    d["r_adj"], d["env"], d["fault"], d["outage"] = r_adj, env, fault, outage

    # ---- نقاط إعادة الضبط (تنظيف مسجّل + ارتفاع مفاجئ غير مسجّل) ----
    dates = d["date"]
    logged = []
    for cd in cleaning_dates or ():
        cd = pd.Timestamp(cd).normalize()
        pos = int(np.searchsorted(dates.values, np.datetime64(cd)))
        if 0 <= pos < len(d):
            logged.append(pos)
    auto = [p for p in _detect_recoveries(env, thresh=0.07 if weather else 0.05) if not any(abs(p - l) <= 6 for l in logged)]
    resets = sorted(set(logged + auto))
    last_pos = len(d) - 1
    seg_starts = [0] + [p for p in resets if p > 0]

    # ---- فاقد الأتربة لكل مقطع بخط أساس خاص ----
    L = np.full(len(d), np.nan)
    base_modes = []
    for k, s0 in enumerate(seg_starts):
        s1 = seg_starts[k + 1] if k + 1 < len(seg_starts) else len(d)
        if k == 0 and 0 not in logged:
            vals = env.iloc[s0:s1].dropna()
            if len(vals) < 3:
                continue
            base, mode = float(vals.quantile(0.95)), "best_observed"
        else:
            vals = r_use.iloc[s0 + 1:s0 + 9].dropna()
            if len(vals) < 3:
                continue
            base, mode = float(vals.quantile(0.85)), "after_cleaning"
        base_modes.append(mode)
        seg = env.iloc[s0:s1]
        L[s0:s1] = np.clip(1 - seg.values / base, 0, 0.45)
        if mode == "after_cleaning":
            L[s0:s0 + 7] = 0.0
    d["L"] = pd.Series(L).ffill().fillna(0.0).values

    # ---- معدل تراكم الأتربة (من المقطع الأخير) ----
    p, C = cfg.tariff_egp_per_kwh, cfg.clean_cost_egp
    seg_start = seg_starts[-1]
    seg_raw = d["L"].iloc[seg_start:].values
    days_since = len(seg_raw)
    x = np.arange(days_since)
    ok = np.isfinite(seg_raw)
    if days_since >= 14 and ok.sum() >= 10:
        slope = float(np.polyfit(x[ok], seg_raw[ok], 1)[0])
        a_hat = slope if slope > 0.0002 else cfg.default_soiling_rate
        a_src = "learned" if slope > 0.0002 else "default"
    else:
        a_hat, a_src = cfg.default_soiling_rate, "default"
    a_hat = float(np.clip(a_hat, 0.0003, 0.004))

    # تصحيح التأخر: الغلاف العلوي (quantile) بيعكس غالبًا أيامًا سابقة (~4 أيام)، فنضيف معدل التراكم × التأخر
    LAG = 4
    pos_in_seg = np.zeros(len(d))
    for k, s0 in enumerate(seg_starts):
        s1 = seg_starts[k + 1] if k + 1 < len(seg_starts) else len(d)
        pos_in_seg[s0:s1] = np.arange(s1 - s0)
    d["L"] = np.clip(d["L"].values + np.where(pos_in_seg >= 10, a_hat * LAG, 0.0), 0, 0.45)

    # ---- اقتصاديات ----
    d["potential"] = np.where(~bad, d["kwh"] / np.clip(1 - d["L"], 0.5, 1), np.nan)
    d["loss_kwh"] = np.where(~bad, d["potential"] - d["kwh"], 0.0)
    seg_df = d.iloc[seg_start:]
    cum_kwh = float(seg_df["loss_kwh"].sum())
    cum_egp = cum_kwh * p
    L_now = float(d["L"].iloc[-1])
    E = float(d["potential"].iloc[-7:].mean(skipna=True)) if d["potential"].iloc[-7:].notna().any() else float(d["kwh"].iloc[-7:].mean())

    aEp = a_hat * E * p
    t_star = float(np.sqrt(2 * C / aEp)) if aEp > 0 else float("inf")
    if cum_egp >= C:
        days_until = 0.0
    else:
        b = L_now * E * p
        days_until = float((-b + np.sqrt(b * b + 2 * aEp * (C - cum_egp))) / aEp) if aEp > 0 else float("inf")

    # ---- الحالة الحالية للأعطال ----
    recent_fault = [e for e in episodes if (d["date"].iloc[-1] - e["end"]).days <= 2]   # عطل شغال دلوقتي أو لسه منتهي من يومين
    past_fault = [e for e in episodes if 2 < (d["date"].iloc[-1] - e["end"]).days <= 21]
    mode = base_modes[-1] if base_modes else "best_observed"
    err = 0.015 + (0.02 if mode == "best_observed" else 0.0) + (0.015 if days_since < 14 else 0.0) + (0.01 if not weather else 0.0) \
        + (0.0 if calib.get("calibrated") else 0.02)   # عدم يقين النموذج (ميل/اتجاه/جو) لو ما اتعايرش

    notes = []
    if mode == "best_observed":
        notes.append("مفيش تنظيف مسجّل: الفاقد المحسوب هو الحد الأدنى (مقارنة بأفضل أداء شفناه). سجّل آخر تنظيف علشان الدقة تتحسن.")
    if days_since < 14:
        notes.append("بيانات قليلة منذ آخر تنظيف: التقدير مبدئي.")
    if a_src == "default":
        notes.append("معدل تراكم الأتربة افتراضي (0.15%/يوم) لحين تجميع بيانات كافية.")
    if calib.get("calibrated"):
        notes.append(f"تمت معايرة الميل الفعّال تلقائيًا من تنظيفاتك المسجّلة: {calib['tilt']:.0f}° (المُدخل كان {calib['original_tilt']:.0f}°).")
    else:
        notes.append("الدقة بتفترض إن الميل والاتجاه المُدخلين صحيحين (خطأ 5° في الميل ممكن يضيف 3 نقاط خطأ). سجّل تنظيفتين لمعايرة تلقائية.")
    if a_src == "learned" and a_hat > 0.0035:
        notes.append("معدل تراكم الأتربة المحسوب أعلى من المعتاد جدًا: راجع الميل والاتجاه والقراءات، أو ممكن يكون في ظل متزايد.")
    for e in past_fault:
        notes.append(f"حصل هبوط غير طبيعي من {e['start'].date()} لمدة {e['days']} أيام ورجع الإنتاج. تأكد إن المشكلة اتحلّت.")
    if auto and (not logged or auto[-1] > max(logged)):
        notes.append("اكتشفنا ارتفاعًا مفاجئًا في الإنتاج (تنظيف أو مطر؟). لو نظفت سجّل التاريخ علشان نعدّل التقدير.")

    if recent_fault:
        decision = "inspect"
    elif L_now < 0.03:
        decision = "ok"
    elif cum_egp >= C:
        decision = "clean_now"
    else:
        decision = "wait"

    return {
        "status": "ok", "decision": decision, "loss_pct": L_now, "loss_err": err, "cum_loss_egp": cum_egp, "cum_loss_kwh": cum_kwh,
        "daily_loss_egp_now": L_now * E * p, "days_until_clean": days_until, "t_star_days": t_star, "rate_per_day": a_hat, "rate_source": a_src,
        "e_daily_kwh": E, "days_since_reset": days_since, "baseline_mode": mode, "weather_mode": weather,
        "episodes": episodes, "recent_fault": recent_fault, "recoveries_auto": [d["date"].iloc[i] for i in auto],
        "calibration": calib, "perf_index_now": float(d["r_adj"].iloc[-7:].median()), "notes": notes, "series": d, "cleaning_cost": C, "tariff": p,
    }


# ---------------------------------------------------------------------------
# معايرة الميل الفعّال: لما يكون فيه تنظيفتين أو أكتر، مستوى الأداء بعد كل تنظيف لازم يكون متساوي تقريبًا.
# لو بينهم فرق منتظم، ده معناه إن نموذج الميل/الاتجاه/الجو مش مطابق (انحراف موسمي) مش أتربة.
# بنبحث عن "ميل فعّال" يقلّل الفرق بين خطوط الأساس. بيحسّن الدقة لما بيانات المستخدم فيها ≥ 2 تنظيف مسجّل.
# ---------------------------------------------------------------------------
def calibrate_effective_tilt(readings: pd.DataFrame, cfg: SystemConfig, cleaning_dates, span: float = 14.0, step: float = 2.0):
    import dataclasses
    cds = sorted(pd.Timestamp(c).normalize() for c in (cleaning_dates or ()))
    d0 = readings.copy()
    d0["date"] = pd.to_datetime(d0["date"]).dt.normalize()
    d0 = d0.dropna(subset=["kwh"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    pos = [int(np.searchsorted(d0["date"].values, np.datetime64(c))) for c in cds]
    pos = [p for p in pos if 0 <= p < len(d0) - 6]
    if len(pos) < 2:
        return cfg, {"calibrated": False, "reason": "محتاجين تنظيفتين مسجّلتين على الأقل للمعايرة"}
    best = None
    for tilt in np.arange(max(0.0, cfg.tilt - span), min(90.0, cfg.tilt + span) + 1e-9, step):
        c2 = dataclasses.replace(cfg, tilt=float(tilt))
        ecs = clear_sky_daily_kwh(c2, d0["date"]).values
        r = np.where(ecs > 3, d0["kwh"].values / ecs, np.nan)
        bases = []
        for p in pos:
            v = r[p + 1:p + 9]
            v = v[np.isfinite(v)]
            if len(v) >= 3:
                bases.append(np.quantile(v, 0.85))
        if len(bases) < 2:
            continue
        cost = float(np.std(bases) / np.mean(bases))
        if best is None or cost < best[0]:
            best = (cost, float(tilt))
    if best is None:
        return cfg, {"calibrated": False, "reason": "بيانات ما بعد التنظيف غير كافية"}
    return dataclasses.replace(cfg, tilt=best[1]), {"calibrated": True, "tilt": best[1], "residual": best[0], "original_tilt": cfg.tilt}
