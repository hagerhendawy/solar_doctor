"""ثيم واجهة Solar Doctor: CSS احترافي (RTL) + مكوّنات HTML (هيرو، كروت مؤشرات، بطاقة القرار)."""
import math

PALETTE = {"navy": "#12355B", "blue": "#2A7FBA", "sun": "#F2A900", "orange": "#E8743B", "green": "#2E8B57", "red": "#C0392B",
           "ink": "#1B2A33", "muted": "#5B6770", "line": "#E3E9EF", "bg": "#F5F7FA"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
:root{--navy:#12355B;--blue:#2A7FBA;--sun:#F2A900;--orange:#E8743B;--green:#2E8B57;--red:#C0392B;--ink:#1B2A33;--muted:#5B6770;--line:#E3E9EF;--bg:#F5F7FA}
.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp li, .stApp button, .stApp input, .stApp textarea,
.stApp span:not([data-testid="stIconMaterial"]) {font-family:'Cairo','Segoe UI',Tahoma,sans-serif;}
.stApp{background:linear-gradient(180deg,#EEF3F9 0%,#F5F7FA 260px);direction:rtl}
#MainMenu, footer {visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1rem;padding-bottom:3rem;max-width:1180px}
.js-plotly-plot, .plotly, .stPlotlyChart{direction:ltr}
h1,h2,h3{color:var(--navy)}

/* ---------- الشريط الجانبي ---------- */
[data-testid="stSidebar"]{background:#fff;border-left:1px solid var(--line)}
[data-testid="stSidebar"] .block-container{padding-top:1rem}
.sb-brand{display:flex;align-items:center;gap:10px;padding:6px 4px 14px;border-bottom:1px solid var(--line);margin-bottom:10px}
.sb-brand .logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,var(--sun),var(--orange));display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 10px rgba(242,169,0,.35)}
.sb-brand b{display:block;color:var(--navy);font-size:1.15rem;line-height:1.1}
.sb-brand small{color:var(--muted)}
.sb-title{color:var(--navy);font-weight:700;font-size:.95rem;margin:14px 0 4px;padding-right:8px;border-right:4px solid var(--sun)}

/* ---------- الهيرو ---------- */
.hero{position:relative;overflow:hidden;border-radius:22px;padding:28px 34px;margin-bottom:18px;color:#fff;
 background:radial-gradient(1200px 400px at 90% -20%,rgba(242,169,0,.35),transparent 60%),linear-gradient(120deg,#0E2A4A 0%,#12355B 45%,#1D5A8E 100%);
 box-shadow:0 14px 34px rgba(18,53,91,.25);display:flex;align-items:center;justify-content:space-between;gap:20px}
.hero h1{color:#fff;margin:0 0 6px;font-weight:800;font-size:2.1rem;line-height:1.2}
.hero p{margin:0 0 14px;color:#D6E4F2;font-size:1.05rem}
.hero .chips span{display:inline-block;margin:0 0 6px 8px;padding:5px 12px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);font-size:.85rem}
.hero .chips span.demo{background:rgba(242,169,0,.25);border-color:rgba(242,169,0,.6);color:#FFE7A8}
.hero svg{flex:0 0 220px;max-width:220px;height:auto;filter:drop-shadow(0 10px 18px rgba(0,0,0,.25))}
@media(max-width:760px){.hero{flex-direction:column;align-items:flex-start;padding:22px}.hero svg{display:none}.hero h1{font-size:1.6rem}}

/* ---------- القرار ---------- */
.decision{display:flex;gap:18px;align-items:center;border-radius:20px;padding:22px 24px;color:var(--ink);border:1px solid var(--line);
 box-shadow:0 8px 24px rgba(18,53,91,.08);min-height:150px;position:relative;overflow:hidden}
.decision:before{content:"";position:absolute;top:0;right:0;bottom:0;width:8px;background:var(--acc)}
.decision .d-ic{flex:0 0 64px;height:64px;border-radius:18px;background:var(--acc);display:flex;align-items:center;justify-content:center;font-size:32px;color:#fff;box-shadow:0 8px 18px rgba(0,0,0,.15)}
.decision .d-lab{font-size:1.65rem;font-weight:800;color:var(--acc);line-height:1.2;margin-bottom:6px}
.decision .d-msg{font-size:1.02rem;line-height:1.85;color:#2D3B45}
.d-good{--acc:#2E8B57;background:linear-gradient(135deg,#F1FAF4,#fff)}
.d-warn{--acc:#E09A00;background:linear-gradient(135deg,#FFF8E8,#fff)}
.d-bad{--acc:#C0392B;background:linear-gradient(135deg,#FDF0EE,#fff)}
.d-neutral{--acc:#5B6770;background:linear-gradient(135deg,#F1F4F7,#fff)}

/* ---------- كروت المؤشرات ---------- */
.kpi{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px 18px;box-shadow:0 6px 18px rgba(18,53,91,.06);position:relative;overflow:hidden;height:100%}
.kpi:after{content:"";position:absolute;left:-18px;bottom:-18px;width:80px;height:80px;border-radius:50%;background:var(--accent);opacity:.08}
.kpi .k-top{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:.9rem;font-weight:600}
.kpi .k-ic{width:32px;height:32px;border-radius:10px;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:16px}
.kpi .k-v{font-size:1.9rem;font-weight:800;color:var(--accent);margin:8px 0 2px;line-height:1.15}
.kpi .k-s{font-size:.82rem;color:var(--muted)}

/* ---------- بطاقات وأقسام ---------- */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px;background:#fff;box-shadow:0 6px 18px rgba(18,53,91,.05)}
.sec{display:flex;align-items:baseline;gap:10px;margin:26px 0 8px}
.sec h3{margin:0;font-size:1.25rem;font-weight:800;color:var(--navy)}
.sec span{color:var(--muted);font-size:.9rem}
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{height:46px;padding:0 18px;border-radius:12px 12px 0 0;font-weight:700;color:var(--muted)}
.stTabs [aria-selected="true"]{color:var(--navy);background:#fff;box-shadow:0 -3px 0 var(--sun) inset}
.note{border-radius:14px;padding:12px 16px;margin:8px 0;background:#FFF8E8;border:1px solid #F3DDA0;color:#5A4500;line-height:1.7}
.note.info{background:#EAF3FB;border-color:#C5DCF0;color:#17405F}
.note.demo{background:#FFF1E6;border-color:#F4C9A5;color:#7A3A0F}
.share{background:#fff;border:1px dashed #C6D3E0;border-radius:16px;padding:16px 18px;line-height:1.9;white-space:pre-wrap;color:#2D3B45}
.tag{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.78rem;font-weight:700;margin-left:6px}
.tag.red{background:#FDE7E4;color:#9C2B1F}.tag.green{background:#E4F4EA;color:#1E6B40}.tag.amber{background:#FFF1CC;color:#7A5B00}
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:12px;font-weight:700}
.footer{margin-top:34px;padding:16px 18px;border-top:1px solid var(--line);color:var(--muted);font-size:.85rem;line-height:1.8;text-align:center}
</style>
"""


def sun_panel_svg() -> str:
    rays = "".join(
        f'<line x1="{165 + 28 * math.cos(a):.1f}" y1="{38 + 28 * math.sin(a):.1f}" x2="{165 + 37 * math.cos(a):.1f}" y2="{38 + 37 * math.sin(a):.1f}" stroke="#F2A900" stroke-width="3" stroke-linecap="round"/>'
        for a in [i * math.pi / 4 for i in range(8)])
    cells = "".join(f'<line x1="{x}" y1="74" x2="{x - 6}" y2="132" stroke="#9FC4E4" stroke-width="1.2" opacity=".7"/>' for x in (68, 96, 124))
    cells += "".join(f'<line x1="44" y1="{y}" x2="158" y2="{y}" stroke="#9FC4E4" stroke-width="1.2" opacity=".7"/>' for y in (92, 112))
    return ('<svg viewBox="0 0 220 150" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><linearGradient id="pg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#3E94D1"/><stop offset="1" stop-color="#0E2A4A"/></linearGradient></defs>'
            f'<circle cx="165" cy="38" r="21" fill="#F2A900"/>{rays}'
            f'<g><polygon points="48,72 168,72 156,134 36,134" fill="url(#pg)" stroke="#fff" stroke-width="2.5"/>{cells}</g>'
            '<rect x="92" y="134" width="12" height="8" fill="#C9D7E6"/><rect x="72" y="142" width="52" height="5" rx="2.5" fill="#C9D7E6"/></svg>')


def hero(is_demo: bool) -> str:
    chip = '<span class="demo">⚠ بيانات محاكاة (تجريبية)</span>' if is_demo else '<span>📈 قراءات حقيقية من ملفك</span>'
    return (f'<div class="hero"><div><h1>☀️ دكتور الألواح الشمسية</h1><p>اعرف إمتى تنضّف ألواحك، وكام بتخسر بالجنيه، وهل في عطل؟</p>'
            f'<div class="chips">{chip}<span>🧮 pvlib</span><span>💰 قرار بالجنيه</span><span>🛠 كشف الأعطال</span></div></div>{sun_panel_svg()}</div>')


DEC_STYLE = {"ok": ("d-good", "✅"), "wait": ("d-warn", "⏳"), "clean_now": ("d-bad", "🧼"), "inspect": ("d-bad", "🔧"), "collect": ("d-neutral", "📥")}


def decision_card(decision: str, label: str, message: str) -> str:
    cls, icon = DEC_STYLE.get(decision, ("d-neutral", "ℹ️"))
    return f'<div class="decision {cls}"><div class="d-ic">{icon}</div><div><div class="d-lab">{label}</div><div class="d-msg">{message}</div></div></div>'


def kpi(icon: str, title: str, value: str, sub: str, accent: str) -> str:
    return (f'<div class="kpi" style="--accent:{accent}"><div class="k-top"><div class="k-ic">{icon}</div>{title}</div>'
            f'<div class="k-v">{value}</div><div class="k-s">{sub}</div></div>')


def section(title: str, sub: str = "") -> str:
    return f'<div class="sec"><h3>{title}</h3><span>{sub}</span></div>'


def note(text: str, kind: str = "") -> str:
    return f'<div class="note {kind}">{text}</div>'
