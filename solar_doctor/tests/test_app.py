from streamlit.testing.v1 import AppTest


def _all_markdown(at):
    return " ".join(m.value for m in at.markdown)


def test_app_runs_demo_mode_without_errors():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    html = _all_markdown(at)
    assert "decision" in html and "kpi" in html and "hero" in html
    assert " DATA "in html


def test_app_with_fault_toggle():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    cb = [c for c in at.sidebar.checkbox if "عطل" in c.label][0]
    cb.set_value(True).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "افحص عطل" in _all_markdown(at)


def test_theme_helpers():
    import ui_theme as T
    assert "d-bad" in T.decision_card("clean_now", "نظّف", "x")
    assert "svg" in T.sun_panel_svg()
    assert "kpi" in T.kpi("i", "t", "v", "s", "#fff")
