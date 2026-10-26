"""رسومات Plotly بتصميم موحّد (ألوان الهوية، خطوط ناعمة، تلميحات عربية)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from engine.sim_policies import policy_cost
from ui_theme import PALETTE as P

FONT = dict(family="Cairo, Segoe UI, Tahoma, sans-serif", size=13, color=P["ink"])


def _base(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(height=height, font=FONT, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=30, b=10),
                      hovermode="x unified", hoverlabel=dict(font=FONT, bgcolor="white"),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12)) if legend else None, showlegend=legend)
    fig.update_xaxes(showgrid=False, linecolor=P["line"], tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#E9EEF3", zeroline=False, tickfont=dict(size=11))
    return fig


def production_fig(s: pd.DataFrame, res: dict, cleaning_dates) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=s["date"], y=s["ecs"], name="أقصى إنتاج ممكن (سماء صافية)", line=dict(color="#9AA9B8", width=1.8, dash="dash"), hovertemplate="%{y:.1f}")
    fig.add_scatter(x=s["date"], y=s["kwh"], name="الإنتاج الفعلي", line=dict(color=P["blue"], width=2.6), fill="tonexty", fillcolor="rgba(232,116,59,.16)", hovertemplate="%{y:.1f}")
    for e in res["episodes"]:
        fig.add_vrect(x0=e["start"], x1=e["end"] + pd.Timedelta(days=1), fillcolor=P["red"], opacity=.13, line_width=0,
                      annotation_text="انقطاع" if e["type"] == "outage" else "هبوط/عطل", annotation_position="top left", annotation_font=dict(size=11, color=P["red"]))
    for cd in cleaning_dates:
        fig.add_vline(x=cd, line_dash="dot", line_color=P["green"], line_width=2)
        fig.add_annotation(x=cd, y=1.02, yref="paper", text="تنظيف", showarrow=False, font=dict(size=11, color=P["green"]))
    fig.update_yaxes(title_text="كيلووات ساعة / يوم")
    return _base(fig)


def soiling_fig(s: pd.DataFrame, truth: pd.DataFrame | None, thresh: float = 3.0) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=s["date"], y=s["L"] * 100, name="تقدير Solar Doctor", line=dict(color=P["orange"], width=3), fill="tozeroy", fillcolor="rgba(232,116,59,.14)", hovertemplate="%{y:.1f}%")
    if truth is not None:
        fig.add_scatter(x=truth["date"], y=truth["soiling_true"] * 100, name="الحقيقة (معروفة في المحاكاة فقط)", line=dict(color=P["muted"], width=2, dash="dash"), hovertemplate="%{y:.1f}%")
    fig.add_hline(y=thresh, line_color=P["green"], line_dash="dashdot", annotation_text="تحت الحد: لا إجراء", annotation_position="bottom right", annotation_font=dict(size=11, color=P["green"]))
    fig.update_yaxes(title_text="فاقد الأتربة %", rangemode="tozero")
    return _base(fig)


def roi_fig(res: dict) -> go.Figure:
    s = res["series"]; seg = s.iloc[-res["days_since_reset"]:]
    cum = (seg["loss_kwh"].cumsum() * res["tariff"]).values
    a, E, p, C = res["rate_per_day"], res["e_daily_kwh"], res["tariff"], res["cleaning_cost"]
    t = np.arange(0, 91)
    proj = cum[-1] + res["loss_pct"] * E * p * t + 0.5 * a * E * p * t ** 2
    fig = go.Figure()
    fig.add_scatter(x=np.arange(-len(cum) + 1, 1), y=cum, name="الخسارة التراكمية (فعلية)", line=dict(color=P["orange"], width=3), fill="tozeroy", fillcolor="rgba(232,116,59,.14)", hovertemplate="%{y:,.0f} جنيه")
    fig.add_scatter(x=t, y=proj, name="توقع", line=dict(color=P["orange"], width=2.4, dash="dash"), hovertemplate="%{y:,.0f} جنيه")
    fig.add_hline(y=C, line_color=P["navy"], line_width=2, annotation_text=f"تكلفة التنظيف {C:,.0f} جنيه", annotation_position="top right", annotation_font=dict(size=12, color=P["navy"]))
    d = res["days_until_clean"]
    if np.isfinite(d) and d <= 90:
        fig.add_scatter(x=[d], y=[C], mode="markers+text", marker=dict(size=13, color=P["green"], line=dict(color="white", width=2)),
                        text=["نقطة التعادل" if d > 0 else "الآن"], textposition="bottom center", textfont=dict(color=P["green"], size=12), name="التعادل", hoverinfo="skip")
    fig.update_xaxes(title_text="أيام (0 = النهارده)"); fig.update_yaxes(title_text="جنيه", rangemode="tozero")
    return _base(fig)


def policy_fig(res: dict, cfg) -> go.Figure:
    E, a, p, C = res["e_daily_kwh"], res["rate_per_day"], res["tariff"], res["cleaning_cost"]
    T = max(5, round(res["t_star_days"]))
    pol = [("بدون تنظيف", None), ("كل 14 يوم", 14), ("كل 30 يوم", 30), (f"ذكي (كل {T} يوم)", T)]
    vals = [policy_cost(180, i, E, a, p, C) for _, i in pol]
    cols = ["#9AA9B8", P["red"], P["orange"], P["green"]]
    fig = go.Figure()
    for (n, _), (tot, nc), c in zip(pol, vals, cols):
        fig.add_bar(x=[n], y=[tot], marker_color=c, text=[f"{tot:,.0f} جنيه<br>{nc} تنظيف"], textposition="outside", name=n, showlegend=False, hoverinfo="skip")
    fig.update_yaxes(title_text="التكلفة الكلية خلال 180 يوم (جنيه)", rangemode="tozero"); fig.update_layout(bargap=.42)
    return _base(fig, height=360, legend=False)


def gauge_fig(loss_pct: float, err_pct: float) -> go.Figure:
    v = loss_pct * 100
    fig = go.Figure(go.Indicator(mode="gauge+number", value=v, number=dict(suffix="%", font=dict(size=40, color=P["navy"], family=FONT["family"]), valueformat=".1f"),
        gauge=dict(axis=dict(range=[0, 25], tickwidth=1, tickcolor=P["line"]), bar=dict(color=P["navy"], thickness=.28), bgcolor="white", borderwidth=0,
                   steps=[dict(range=[0, 3], color="#CDEBD8"), dict(range=[3, 10], color="#FBE7A9"), dict(range=[10, 25], color="#F4B9B0")],
                   threshold=dict(line=dict(color=P["red"], width=3), thickness=.8, value=min(25, v + err_pct)))))
    fig.update_layout(height=230, margin=dict(l=18, r=18, t=36, b=0), paper_bgcolor="rgba(0,0,0,0)", font=FONT,
                      title=dict(text="فاقد الأتربة الحالي", x=.5, font=dict(size=15, color=P["muted"])))
    return fig
