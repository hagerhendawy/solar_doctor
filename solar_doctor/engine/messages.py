"""رسائل عربية بسيطة للمستخدم (واتساب/الواجهة) من نتيجة المحرك."""
from __future__ import annotations
import pandas as pd

LABELS = {"ok": "الألواح بحالة كويسة", "wait": "استنى شوية", "clean_now": "نظّف دلوقتي", "inspect": "افحص عطل", "collect": "محتاجين بيانات أكتر"}
TONES = {"ok": "good", "wait": "warn", "clean_now": "bad", "inspect": "bad", "collect": "neutral"}


def _fmt(x, nd=0):
    return f"{x:,.{nd}f}"


def make_message(res: dict) -> str:
    if res.get("status") != "ok":
        return "محتاجين على الأقل 7 أيام من قراءات الإنتاج علشان نبدأ التحليل."
    L, err = res["loss_pct"] * 100, res["loss_err"] * 100
    cum, C = res["cum_loss_egp"], res["cleaning_cost"]
    dec = res["decision"]
    last = pd.Timestamp(res["series"]["date"].iloc[-1])
    if dec == "inspect":
        ep = res["recent_fault"][0]
        if ep["type"] == "outage":
            core = f"الإنتاج قريب من الصفر من {ep['start'].date()}. غالبًا قطع كهرباء أو الإنفرتر واقف. افحص الإنفرتر والقواطع."
        else:
            core = (f"الإنتاج نازل بشكل مفاجئ حوالي {ep['severity']*100:.0f}% من {ep['start'].date()} لمدة {ep['days']} أيام. "
                    "ده مش شكل الأتربة (الأتربة بتتراكم ببطء). الأسباب المحتملة: ظل جديد، سلسلة ألواح فاصلة، عطل إنفرتر، أو لوح مكسور. افحص قبل ما تنظف.")
        return core
    if dec == "ok":
        return (f"فاقد الأتربة حوالي {L:.0f}% (±{err:.0f}) وده أقل من الحد اللي يستاهل عنده التنظيف. "
                f"خسارتك من آخر تنظيف حوالي {_fmt(cum)} جنيه، مقابل تكلفة تنظيف {_fmt(C)} جنيه. مفيش داعي تنظف دلوقتي.")
    if dec == "clean_now":
        return (f"فاقد الأتربة حوالي {L:.0f}% (±{err:.0f}). خسارتك من آخر تنظيف وصلت {_fmt(cum)} جنيه، يعني تعدّت تكلفة التنظيف ({_fmt(C)} جنيه). "
                f"كل يوم تأخير بيكلّفك حوالي {_fmt(res['daily_loss_egp_now'])} جنيه. الأفضل تنظف خلال أيام.")
    d = res["days_until_clean"]
    when = (last + pd.Timedelta(days=round(d))).date()
    return (f"فاقد الأتربة حوالي {L:.0f}% (±{err:.0f}). خسارتك من آخر تنظيف حوالي {_fmt(cum)} جنيه، ولسه أقل من تكلفة التنظيف ({_fmt(C)} جنيه). "
            f"التنظيف هيستاهل بعد حوالي {d:.0f} يوم (تقريبًا {when}). الفاصل الأمثل بين كل تنظيفتين لنظامك حوالي {res['t_star_days']:.0f} يوم.")
