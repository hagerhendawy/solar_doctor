"""حساب تكلفة سياسات التنظيف (فاقد الأتربة + تكلفة التنظيف) خلال فترة، لمقارنة التنظيف الثابت بالذكي."""


def policy_cost(days: int = 180, interval=None, E: float = 26.0, a: float = 0.0015, p: float = 2.0, C: float = 300.0):
    """interval=None: بدون تنظيف. بيرجّع (التكلفة الكلية بالجنيه، عدد مرات التنظيف). افتراض فقد خطي."""
    s, tot, n = 0.0, 0.0, 0
    for day in range(1, days + 1):
        s += a
        tot += s * E * p
        if interval and day % interval == 0:
            s = 0.0; tot += C; n += 1
    return tot, n
