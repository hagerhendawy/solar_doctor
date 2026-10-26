"""يولّد docs/results.json: كل أرقام الدقة المذكورة في الوثائق (علشان الأرقام في الـREADME والـPDF تطلع من تشغيل فعلي)."""
import json, time
import numpy as np
import pandas as pd
from engine.config import SystemConfig
from engine.synth import Scenario, make_scenario, random_scenario
from engine.analyze import analyze
from evaluate import run, summarize

t0 = time.time()
out = {}
out["matched_100"] = summarize(run(100))
out["no_logged_cleaning_100"] = summarize(run(100, log_cleaning=False))
out["kwp30_100"] = summarize(run(100, kwp=30.0))
out["weather_mode_60"] = summarize(run(60, weather=True))
out["mismatch_one_cleaning_100"] = summarize(run(100, mismatch=True))
out["mismatch_two_cleanings_raw_40"] = summarize(run(40, mismatch=True, two_cleanings=True, calibrate=False))
out["mismatch_two_cleanings_calibrated_40"] = summarize(run(40, mismatch=True, two_cleanings=True, calibrate=True))
# حساسية كل عامل (تنظيفة واحدة)
base = SystemConfig()
cases = [("لا اختلاف", {}), ("فواقد النظام 10% بدل 14%", dict(system_loss=0.10)), ("حرارة (NOCT 48)", dict(noct=48.0, gamma=-0.0035)),
         ("ميل أقل 5 درجات", dict(tilt=23.0)), ("ميل أقل 10 درجات", dict(tilt=18.0)), ("اتجاه منحرف 20 درجة", dict(azimuth=160.0)),
         ("اتجاه منحرف 40 درجة", dict(azimuth=140.0)), ("جو أغبر (AOD 0.25)", dict(aod700=0.25)), ("بخار ماء مختلف", dict(precipitable_water=3.0))]
sens = []
for label, kw in cases:
    true = SystemConfig(**kw); errs = []
    for seed in range(30):
        sc = random_scenario(seed, with_fault=False)
        df = make_scenario(base, sc, true)
        r = analyze(df[["date", "kwh"]], base, cleaning_dates=[df.date.iloc[sc.clean_days[0] - 1]])
        errs.append(r["loss_pct"] - df.soiling_true.iloc[-1])
    sens.append({"label": label, "bias_pp": round(float(np.mean(errs) * 100), 2), "mae_pp": round(float(np.mean(np.abs(errs)) * 100), 2)})
out["sensitivity"] = sens
# توزيع الخطأ في الحالة الأساسية
r = run(100)
out["error_hist_pp"] = [round(float(x * 100), 2) for x in r["err"]]
# مثال تشغيل واحد للرسوم
cfg = SystemConfig()
sc = Scenario(days=120, seed=3, clean_days=(40,), storm_days=(22,))
df = make_scenario(cfg, sc)
res = analyze(df[["date", "kwh"]], cfg, cleaning_dates=[df.date.iloc[39]])
s = res["series"]
out["example"] = {"dates": [str(x.date()) for x in s["date"]], "kwh": [round(float(x), 2) for x in s["kwh"]], "ecs": [round(float(x), 2) for x in s["ecs"]],
                  "L_est": [round(float(x), 4) for x in s["L"]], "L_true": [round(float(x), 4) for x in df["soiling_true"]],
                  "decision": res["decision"], "cum_loss_egp": round(res["cum_loss_egp"]), "days_until": round(res["days_until_clean"], 1), "t_star": round(res["t_star_days"], 1)}
out["_meta"] = {"seconds": round(time.time() - t0), "note": "كل الأرقام من محاكاة. الواقع محتاج تجربة تنظيف حقيقية."}
json.dump(out, open("docs/results.json", "w"), ensure_ascii=False, indent=1)
print("done", round(time.time() - t0), "s")
