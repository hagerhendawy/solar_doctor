"""إعدادات النظام الشمسي (بيدخلها المستخدم مرة واحدة)."""
from dataclasses import dataclass, asdict


@dataclass
class SystemConfig:
    lat: float = 30.04            # خط العرض (القاهرة كمثال)
    lon: float = 31.24            # خط الطول
    kwp: float = 6.0              # قدرة النظام بالكيلووات (kWp)
    tilt: float = 28.0            # ميل الألواح (درجة)
    azimuth: float = 180.0        # الاتجاه: 180 = جنوب
    tz: str = "Africa/Cairo"
    altitude: float = 23.0
    tariff_egp_per_kwh: float = 2.0   # قيمة الكيلووات ساعة بالجنيه (من فاتورتك أو سعر صافي القياس)
    clean_cost_egp: float = 300.0     # تكلفة تنظيف واحدة بالجنيه
    system_loss: float = 0.14         # فواقد النظام (أسلاك، إنفرتر...)
    gamma: float = -0.004             # معامل الحرارة (لكل درجة)
    noct: float = 45.0
    aod700: float = 0.12              # تعكير الجو (افتراض لمصر)
    precipitable_water: float = 1.5   # بخار الماء (سم)
    default_soiling_rate: float = 0.0015  # معدل فقد الأتربة اليومي الافتراضي (0.15%/يوم) لحين تعلّم معدل النظام

    def to_dict(self):
        return asdict(self)
