"""واجهة Solar Doctor (Streamlit). التشغيل: streamlit run app.py"""
import io
import json
import urllib.parse

import numpy as np
import pandas as pd
import streamlit as st

from engine.config import SystemConfig
from engine.synth import Scenario, make_scenario
from engine.analyze import analyze
from engine.messages import make_message, LABELS, TONES
import ui_theme as T
import ui_charts as C

st.set_page_config(page_title="Solar Doctor | دكتور الألواح الشمسية", page_icon="☀️", layout="wide", initial_sidebar_state="expanded")
st.markdown(T.CSS, unsafe_allow_html=True)

# ======================= الشريط الجانبي =======================
with st.sidebar:
    st.markdown('<div class="sb-brand"><div class="logo">☀️</div><div><b>Solar Doctor</b><small>دكتور الألواح الشمسية</small></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-title">🏠 بيانات النظام</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    lat = c1.number_input("خط العرض", value=30.04, format="%.3f")
    lon = c2.number_input("خط الطول", value=31.24, format="%.3f")
    kwp = st.number_input("قدرة النظام (كيلووات)", value=6.0, min_value=0.5, step=0.5)
    c3, c4 = st.columns(2)
    tilt = c3.number_input("ميل الألواح °", value=28.0, min_value=0.0, max_value=90.0, help="قيسه بتطبيق ميل في الموبايل: ده أهم إعداد للدقة")
    az = c4.number_input("الاتجاه °", value=180.0, min_value=0.0, max_value=360.0, help="180 = جنوب")
    st.markdown('<div class="sb-title">💰 التكاليف</div>', unsafe_allow_html=True)
    tariff = st.number_input("قيمة الكيلووات ساعة (جنيه)", value=2.0, min_value=0.1, step=0.1)
    clean_cost = st.number_input("تكلفة التنظيف الواحد (جنيه)", value=300.0, min_value=10.0, step=50.0)
    cfg = SystemConfig(lat=lat, lon=lon, kwp=kwp, tilt=tilt, azimuth=az, tariff_egp_per_kwh=tariff, clean_cost_egp=clean_cost)

    st.markdown('<div class="sb-title">📊 مصدر القراءات</div>', unsafe_allow_html=True)
    mode = st.radio("مصدر القراءات", ["بيانات محاكاة (تجريبية)", "رفع ملف CSV"], index=0, label_visibility="collapsed")
    cleaning_txt = st.text_input("تواريخ التنظيف", value="", placeholder="2026-09-10, 2026-10-25", help="YYYY-MM-DD مفصولة بفاصلة. سجّل كل تنظيف: ده أهم عامل في الدقة. تنظيفتان أو أكتر = معايرة تلقائية.")

truth = None
is_demo = mode.startswith("بيانات")
if is_demo:
    with st.sidebar:
        st.markdown('<div class="sb-title">🧪 إعدادات المحاكاة</div>', unsafe_allow_html=True)
        days = st.slider("عدد الأيام", 45, 180, 120)
        rate = st.slider("معدل فقد الأتربة اليومي %", 0.05, 0.40, 0.15, 0.01) / 100
        clean_day = st.slider("يوم آخر تنظيف", 0, days - 10, min(40, days - 10), help="0 = بدون تنظيف")
        storm = st.checkbox("عاصفة ترابية", value=True)
        fault = st.checkbox("عطل في سلسلة ألواح (شغال حاليًا)", value=False)
        seed = st.number_input("Seed (تغيير العشوائية)", value=3, step=1)
    sc = Scenario(days=days, soil_rate=rate, clean_days=(clean_day,) if clean_day > 0 else (), storm_days=(max(5, days // 5),) if storm else (),
                  fault=(days - 6, 8, 0.33) if fault else None, seed=int(seed))
    full = make_scenario(cfg, sc)
    readings, truth = full[["date", "kwh"]], full
    if clean_day > 0 and not cleaning_txt.strip():
        cleaning_txt = str(full["date"].iloc[clean_day - 1].date())
else:
    up = st.file_uploader("ارفع ملف الإنتاج اليومي (CSV)", type=["csv"], help="عمودان: date و kwh")
    if up is None:
        st.markdown(T.hero(False), unsafe_allow_html=True)
        st.markdown(T.section("ابدأ في 3 خطوات"), unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.markdown(T.kpi("1️⃣", "جهّز القراءات", "CSV", "عمودان: date و kwh (إنتاج اليوم بالكيلووات ساعة من شاشة الإنفرتر)", T.PALETTE["blue"]), unsafe_allow_html=True)
        b.markdown(T.kpi("2️⃣", "أدخل إعدادات النظام", "القدرة والميل", "الميل والاتجاه الدقيقين هم أهم عامل في الدقة", T.PALETTE["orange"]), unsafe_allow_html=True)
        c.markdown(T.kpi("3️⃣", "سجّل تواريخ التنظيف", "القرار بالجنيه", "نظّف الآن / استنى / افحص عطل", T.PALETTE["green"]), unsafe_allow_html=True)
        st.markdown(T.note("مثال جاهز في المشروع: <b>data/demo_readings.csv</b>", "info"), unsafe_allow_html=True)
        st.stop()
    readings = pd.read_csv(up)
    readings.columns = [c.strip().lower() for c in readings.columns]
    if not {"date", "kwh"} <= set(readings.columns):
        st.error("الملف لازم يحتوي أعمدة: date و kwh")
        st.stop()

cleaning_dates = []
for t in [x.strip() for x in cleaning_txt.split(",") if x.strip()]:
    try:
        cleaning_dates.append(pd.Timestamp(t))
    except Exception:  # noqa: BLE001
        st.sidebar.error(f"تاريخ غير صالح: {t}")


@st.cache_data(show_spinner=False)
def run(readings_json: str, cfg_json: str, cleaning: tuple):
    r = pd.read_json(io.StringIO(readings_json))
    return analyze(r, SystemConfig(**json.loads(cfg_json)), cleaning_dates=cleaning)


with st.spinner("جاري التحليل..."):
    res = run(readings.to_json(date_format="iso"), json.dumps(cfg.to_dict()), tuple(cleaning_dates))

# ======================= الهيرو =======================
st.markdown(T.hero(is_demo), unsafe_allow_html=True)
if is_demo:
    st.markdown(T.note( "demo"), unsafe_allow_html=True)

if res.get("status") != "ok":
    st.markdown(T.decision_card("collect", LABELS["collect"], make_message(res)), unsafe_allow_html=True)
    st.stop()

# ======================= القرار + العداد =======================
dec = res["decision"]
msg = make_message(res)
left, right = st.columns([2.3, 1])
with left:
    st.markdown(T.decision_card(dec, LABELS[dec], msg), unsafe_allow_html=True)
with right:
    with st.container(border=True):
        st.plotly_chart(C.gauge_fig(res["loss_pct"], res["loss_err"] * 100), width="stretch", config={"displayModeBar": False})
        st.caption(f"هامش عدم اليقين ± {res['loss_err']*100:.1f} نقطة")

# ======================= المؤشرات =======================
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
k1.markdown(T.kpi("💸", "خسارة منذ آخر تنظيف", f"{res['cum_loss_egp']:,.0f} جنيه", f"{res['cum_loss_kwh']:,.0f} كيلووات ساعة ضايعة", T.PALETTE["orange"]), unsafe_allow_html=True)
k2.markdown(T.kpi("🧽", "تكلفة التنظيف", f"{res['cleaning_cost']:,.0f} جنيه", f"خسارة اليوم حوالي {res['daily_loss_egp_now']:,.0f} جنيه", T.PALETTE["blue"]), unsafe_allow_html=True)
days_txt = "الآن" if res["days_until_clean"] <= 0 else f"{res['days_until_clean']:.0f} يوم"
k3.markdown(T.kpi("⏱", "موعد التنظيف المجدي", days_txt, "حتى تعادل الخسارة التكلفة", T.PALETTE["green"]), unsafe_allow_html=True)
k4.markdown(T.kpi("🔁", "الفاصل الأمثل", f"{res['t_star_days']:.0f} يوم", f"معدل الفقد {res['rate_per_day']*100:.2f}% يوميًا ({'متعلَّم' if res['rate_source']=='learned' else 'افتراضي'})", T.PALETTE["navy"]), unsafe_allow_html=True)

# ======================= الرسومات =======================
s = res["series"]
st.markdown(T.section("التحليل التفصيلي", "مرّر الماوس على الرسم لقراءة القيم"), unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["⚡ الإنتاج", "🌫️ فاقد الأتربة", "💰 اقتصاديات التنظيف", "🧾 التفاصيل"])
cfg_plot = {"displayModeBar": False}
with tab1:
    st.plotly_chart(C.production_fig(s, res, cleaning_dates), width="stretch", config=cfg_plot)
    st.caption("المنطقة البرتقالية بين الخطين = الإنتاج الضايع. المناطق الحمراء = أيام اتصنّفت عطل أو انقطاع. الخطوط الخضراء = تواريخ التنظيف.")
with tab2:
    st.plotly_chart(C.soiling_fig(s, truth), width="stretch", config=cfg_plot)
    st.caption("لو الفاقد تحت 3% بنعتبره داخل نطاق الخطأ ('لا إجراء').")
with tab3:
    a1, a2 = st.columns([1.15, 1])
    with a1:
        st.markdown("**متى يستاهل التنظيف؟**")
        st.plotly_chart(C.roi_fig(res), width="stretch", config=cfg_plot)
    with a2:
        st.markdown("**مقارنة سياسات التنظيف**")
        st.plotly_chart(C.policy_fig(res, cfg), width="stretch", config=cfg_plot)
    st.markdown(T.note("القاعدة: نظّف لما الخسارة التراكمية تساوي تكلفة التنظيف. لو الفقد بيزيد بمعدل ثابت ده التوقيت الأمثل رياضيًا. المقارنة تقريبية وبتفترض فقدًا خطيًا.", "info"), unsafe_allow_html=True)
with tab4:
    d1, d2, d3 = st.columns(3)
    d1.metric("أيام منذ آخر تنظيف/بداية القياس", res["days_since_reset"])
    d2.metric("أسلوب خط الأساس", "بعد التنظيف" if res["baseline_mode"] == "after_cleaning" else "أفضل أداء ملاحَظ")
    cal = res.get("calibration", {})
    d3.metric("معايرة الميل", f"{cal['tilt']:.0f}°" if cal.get("calibrated") else "غير مفعّلة")
    for n in res["notes"]:
        st.markdown(T.note("💡 " + n), unsafe_allow_html=True)
    if res["episodes"]:
        st.markdown("**أعطال وانقطاعات مكتشفة**")
        ep = pd.DataFrame(res["episodes"]).copy()
        ep["start"], ep["end"] = ep["start"].dt.date, ep["end"].dt.date
        ep["type"] = ep["type"].map({"drop": "هبوط/عطل", "outage": "انقطاع"})
        ep["severity"] = (ep["severity"] * 100).round(0).astype(int).astype(str) + "%"
        st.dataframe(ep.rename(columns={"start": "البداية", "end": "النهاية", "days": "الأيام", "severity": "الشدة", "type": "النوع"}), width="stretch", hide_index=True)
    with st.expander("إزاي اتحسب ده؟"):
        st.markdown("""
1. بنحسب **أقصى إنتاج ممكن** لكل يوم (سماء صافية) بمكتبة pvlib من موقعك وميل واتجاه وقدرة نظامك.
2. بنقسم إنتاجك الفعلي عليه = **مؤشر الأداء**. الغيوم بتنزّله يوم أو اتنين بس، والأتربة بتنزّل **الغلاف العلوي** ببطء.
3. فاقد الأتربة = 1 − (الغلاف الحالي ÷ الغلاف بعد آخر تنظيف) مع تصحيح تأخر الغلاف.
4. هبوط مفاجئ ومستمر = ظل/عطل. صفر = انقطاع. ارتفاع مفاجئ = تنظيف أو مطر.
5. الخسارة بالجنيه = الفاقد × الإنتاج المتوقع × سعر الكيلووات ساعة. ولما تساوي تكلفة التنظيف: نظّف.""")

# ======================= المشاركة =======================
st.markdown(T.section("شارك النتيجة", "رسالة جاهزة بالعربي"), unsafe_allow_html=True)
share_text = f"☀️ Solar Doctor\n{LABELS[dec]}: {msg}"
st.markdown(f'<div class="share">{share_text}</div>', unsafe_allow_html=True)
b1, b2, _ = st.columns([1, 1, 2])
b1.link_button("📲 مشاركة على واتساب", "https://wa.me/?text=" + urllib.parse.quote(share_text), width="stretch")
b2.download_button("⬇️ تحميل القراءات (CSV)", readings.to_csv(index=False).encode("utf-8-sig"), "readings.csv", "text/csv", width="stretch")

st.markdown('<div class="footer">Solar Doctor • الأرقام تقديرات استرشادية مبنية على نموذج pvlib وافتراضات معلنة، وليست قياسًا مطلقًا. '
            'الدقة المذكورة في الوثائق على بيانات محاكاة، وتحتاج تأكيدًا باختبار تنظيف على أنظمة حقيقية.</div>', unsafe_allow_html=True)
