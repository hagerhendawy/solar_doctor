"""تقييم دقة المحرك على سيناريوهات محاكاة عشوائية (الحقيقة معروفة).
تشغيل: python evaluate.py [عدد السيناريوهات]
تنبيه: دي دقة على محاكاة. لازم تتأكد على بيانات حقيقية (اختبار التنظيف) قبل ما تدّعي دقة في الواقع."""
import sys
import numpy as np
import pandas as pd
from engine.config import SystemConfig
from engine.synth import make_scenario, random_scenario
from engine.analyze import analyze


def run(n=40, weather=False, log_cleaning=True, kwp=6.0, mismatch=False, two_cleanings=False, calibrate=True, true_kw=None):
    cfg = SystemConfig(kwp=kwp)
    true_cfg = SystemConfig(kwp=kwp, aod700=0.25, tilt=22.0, system_loss=0.10, noct=48.0, gamma=-0.0035) if mismatch else None
    if true_kw:
        true_cfg = SystemConfig(kwp=kwp, **true_kw)
    rows = []
    for seed in range(n):
        sc = random_scenario(seed, with_fault=(seed % 2 == 0))
        if two_cleanings:
            sc.clean_days = (int(sc.clean_days[0] % 30 + 25), int(sc.clean_days[0] % 30 + 70))
            sc.days = 150
        df = make_scenario(cfg, sc, true_cfg)
        # نقيّم على نقطة عشوائية قبل نهاية العطل بوقت كافٍ وبعدها
        end = len(df)
        cd = [df["date"].iloc[c - 1] for c in sc.clean_days] if log_cleaning else []
        res = analyze(df[["date", "kwh"] + (["kt_sat"] if weather else [])], cfg, cleaning_dates=cd, use_weather=weather, auto_calibrate=calibrate)
        true_L = float(df["soiling_true"].iloc[-1])
        # الحقيقة المرجعية للقرار: الخسارة التراكمية الحقيقية منذ آخر تنظيف
        seg = df.iloc[sc.clean_days[-1] - 1:]
        potential = seg["kwh"] / (1 - seg["fault_true"]) / (1 - seg["soiling_true"])
        true_cum = float(((potential - potential * (1 - seg["soiling_true"])) * ~seg["outage_true"]).sum() * cfg.tariff_egp_per_kwh)
        fault_true = sc.fault is not None and (sc.fault[0] + sc.fault[1] - 1) >= end - 1
        rows.append({"seed": seed, "L_true": true_L, "L_est": res["loss_pct"], "err": res["loss_pct"] - true_L, "cum_true": true_cum, "cum_est": res["cum_loss_egp"],
                     "fault_in_scenario": sc.fault is not None, "fault_detected": any(e["type"] == "drop" for e in res["episodes"]),
                     "decision": res["decision"], "auto_recoveries": len(res["recoveries_auto"])})
    return pd.DataFrame(rows)


def summarize(df):
    out = {"عدد السيناريوهات": len(df), "متوسط الخطأ المطلق في الفاقد (نقاط مئوية)": round(float(df.err.abs().mean() * 100), 2),
           "الانحياز (تقدير - حقيقة، نقاط)": round(float(df.err.mean() * 100), 2),
           "نسبة سيناريوهات الخطأ ≤ 3 نقاط": round(float((df.err.abs() <= 0.03).mean() * 100), 1)}
    f = df[df.fault_in_scenario]; nf = df[~df.fault_in_scenario]
    out["اكتشاف الأعطال (Recall %)"] = round(float(f.fault_detected.mean() * 100), 1) if len(f) else None
    out["إنذارات عطل كاذبة بدون عطل (%)"] = round(float(nf.fault_detected.mean() * 100), 1) if len(nf) else None
    nf2 = df[~df.fault_in_scenario]
    out["الانحياز بدون أعطال (نقاط)"] = round(float(nf2.err.mean() * 100), 2) if len(nf2) else None
    out["متوسط الخطأ المطلق بدون أعطال (نقاط)"] = round(float(nf2.err.abs().mean() * 100), 2) if len(nf2) else None
    out["متوسط خطأ الخسارة التراكمية (جنيه)"] = round(float((df.cum_est - df.cum_true).abs().mean()), 0)
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    for w in (False, True):
        r = run(n, weather=w)
        print("\n=== بيانات سحب خارجية:", w, "===")
        for k, v in summarize(r).items():
            print(f"{k}: {v}")
