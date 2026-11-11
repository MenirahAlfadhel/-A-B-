"""الجزء 3: إنشاء البيانات وفحوص الثقة"""

from part2_sample_size import *

# ======================== 5. إنشاء البيانات بالمحاكاة ========================
def simulate_experiment(cfg, duration_days):
    """كل المستخدمين الذين يدخلون خلال مدة التجربة (المدة مضروبة في عدد المستخدمين اليومي)."""
    r = np.random.default_rng(cfg["seed"])
    n = duration_days * cfg["daily_new_users"]
    is_b = (r.random(n) < cfg["treatment_share"]).astype(int)
    day = r.integers(1, duration_days + 1, n)
    activity = r.normal(0, 1, n)                                             # نشاط المستخدم (لا نقيسه مباشرة)
    base = cfg["baseline_conversion"]
    logit = np.log(base / (1 - base)) + cfg["activity_strength"] * activity
    p0 = 1 / (1 + np.exp(-logit))
    p0 = np.clip(p0 * base / p0.mean(), 0, 1)                                # نضبط المتوسط ليساوي خط الأساس
    pre_orders_90d = r.poisson(5 * p0 / base)                                # الطلبات في آخر 90 يومًا
    lift = cfg["true_lift_abs"] * (1 + cfg["novelty_boost"] * np.exp(-(day - 1) / 3))
    ordered = r.binomial(1, np.clip(p0 + lift * is_b, 0, 1))
    value = np.maximum(10, r.normal(cfg["order_value_mean"] + cfg["order_value_effect"] * is_b, cfg["order_value_sd"]))
    order_value = np.where(ordered == 1, value, np.nan)
    revenue = ordered * value
    profit = ordered * (cfg["margin"] * value - cfg["extra_cost_per_order_b"] * is_b)
    cancelled = np.where(ordered == 1, r.binomial(1, np.clip(cfg["cancel_rate"] + cfg["cancel_effect"] * is_b, 0, 1)), np.nan)
    support = r.binomial(1, np.clip(cfg["support_rate"] + cfg["support_effect"] * is_b, 0, 1))
    df = pd.DataFrame({"variant": np.where(is_b == 1, "B", "A"), "day": day, "pre_orders_90d": pre_orders_90d,
                       "ordered": ordered, "order_value": order_value, "revenue": revenue, "profit": profit,
                       "cancelled": cancelled, "contacted_support": support})
    if cfg["srm_bug_share"] > 0:                                              # خلل: سجلات ضائعة من B لقليلي النشاط
        lost = (df["variant"] == "B") & (activity < 0) & (r.random(n) < cfg["srm_bug_share"] * 2)
        df = df[~lost]
    return df.reset_index(drop=True)


data = simulate_experiment(CONFIG, days)
say(f"عدد المستخدمين: {len(data):,}")
data.insert(0, "user_id", range(1, len(data) + 1))   # معرّف لكل مستخدم لفحص التكرار
print(data.head())

# ---- فحوص جودة البيانات ----
expected_rows = days * CONFIG["daily_new_users"]
say(f"اكتمال البيانات: {len(data):,} سجل من {expected_rows:,} متوقع")
say(f"السجلات المكررة (نفس المستخدم): {data['user_id'].duplicated().sum()}")
missing = data.isna().sum()
say("القيم المفقودة لكل عمود:")
print(missing.to_string())
non_orderers = (data["ordered"] == 0).sum()
say(f"القيم المفقودة في order_value وcancelled = عدد من لم يطلب ({non_orderers:,})، أي أنها متوقعة وليست خللًا")
assert missing["order_value"] == non_orderers and missing["cancelled"] == non_orderers

data.to_csv(DATA_DIR / "dataset.csv", index=False)
say("حُفظت البيانات في data/dataset.csv")


# ======================== 6. فحوص الثقة ========================
counts = data["variant"].value_counts()
srm_p = srm_check(counts.get("A", 0), counts.get("B", 0), CONFIG["treatment_share"])
if srm_p < 0.001:
    raise SystemExit("توقف التحليل: خلل في نسبة التوزيع (SRM)")
