"""الجزء 2: حجم العينة والمدة"""

from part1_tools import *

# ======================== 3. حجم العينة والمدة ========================
CONFIG = {
    "project": "التوصيل المجاني للطلبات فوق 100 ريال",
    # ---- التصميم (تعرفه قبل التجربة) ----
    "baseline_conversion": 0.10,   # نسبة الطلب الحالية
    "mde_abs": 0.010,              # أصغر أثر مجدٍ تجاريًا: نقطة مئوية واحدة
    "alpha": 0.05,
    "power": 0.80,
    "daily_new_users": 5_000,      # عدد المستخدمين الجدد في اليوم
    "treatment_share": 0.5,
    # ---- المحاكاة ("الحقيقة" المخفية) ----
    "true_lift_abs": 0.012,        # التوصيل المجاني يرفع الطلب 1.2 نقطة
    "order_value_mean": 120,
    "order_value_sd": 50,
    "order_value_effect": 6,       # المستخدم يضيف منتجات ليصل إلى 100 ريال
    "margin": 0.25,
    "extra_cost_per_order_b": 6,   # متوسط تكلفة التوصيل التي تتحملها الشركة لكل طلب
    "cancel_rate": 0.05, "cancel_effect": 0.002,   # بعض من يزيدون السلة يلغون لاحقًا
    "support_rate": 0.03, "support_effect": 0.000,
    "activity_strength": 0.8,
    "novelty_boost": 0.3,          # حماس في أول أيام العرض ثم يهدأ
    "srm_bug_share": 0.0,
    "seed": 2026,
}

c = CONFIG
n_per_group = n_per_group_proportions(c["baseline_conversion"], c["baseline_conversion"] + c["mde_abs"], c["alpha"], c["power"])
days = duration_days(n_per_group, c["daily_new_users"])
say(f"المشروع: {c['project']}")
say(f"حجم العينة: {n_per_group:,} في كل مجموعة، أي {2 * n_per_group:,} مستخدم في المجموع")
say(f"المدة: {days} يومًا، وعدد الأسابيع الكاملة: {days // 7}")
n_planned = days * c["daily_new_users"] // 2
say(f"عدد المستخدمين المتوقع خلال المدة: {n_planned:,} في كل مجموعة")
for label, n_g in [("في المدة المخططة", n_planned), ("إذا اكتفينا بأسبوع واحد", 7 * c["daily_new_users"] // 2)]:
    m = mde_proportions(c["baseline_conversion"], n_g, c["alpha"], c["power"])
    say(f"{label}: أصغر أثر قابل للاكتشاف حوالي {m * 100:.2f} نقطة")
