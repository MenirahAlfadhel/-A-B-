"""الجزء 4: التحليل والتقرير
يُشغَّل من main.py"""

from part3_data_and_trust import *

# ======================== 7. التحليل ========================
# ---- 7.1 المقياس الرئيسي، مع CUPED ----
A, B = data[data.variant == "A"], data[data.variant == "B"]
primary = diff_ci(A["ordered"], B["ordered"])

theta = np.cov(data["ordered"], data["pre_orders_90d"])[0, 1] / data["pre_orders_90d"].var(ddof=1)
adjusted = data["ordered"] - theta * (data["pre_orders_90d"] - data["pre_orders_90d"].mean())
primary_cuped = diff_ci(adjusted[data.variant == "A"], adjusted[data.variant == "B"])

out = pd.DataFrame([primary, primary_cuped], index=["بدون تعديل", "مع CUPED"])
out[["الفرق", "أدنى 95%", "أعلى 95%"]] *= 100
say(f"نسبة الطلب في A: {A['ordered'].mean():.2%}، وفي B: {B['ordered'].mean():.2%}")
say(f"انخفاض التباين بطريقة CUPED: {1 - (primary_cuped['SE'] / primary['SE']) ** 2:.0%}")

# إضافة: الأثر النسبي، ومقارنة التقدير بالأثر الحقيقي في المحاكاة
rel_lift = primary["الفرق"] / A["ordered"].mean()
true_avg_lift = CONFIG["true_lift_abs"] * (1 + CONFIG["novelty_boost"] * np.exp(-(data["day"] - 1) / 3)).mean()
say(f"الأثر النسبي: {rel_lift:.1%}")
say(f"الأثر الحقيقي في المحاكاة: {true_avg_lift * 100:.2f} نقطة، وهو داخل فترة الثقة: {primary['أدنى 95%'] <= true_avg_lift <= primary['أعلى 95%']}")
print(out.round(3))
out.round(4).to_csv(RESULTS_DIR / "primary_metric.csv", encoding="utf-8-sig")

# رسم: الأثر مع فترة الثقة، مقارنة بالأثر المستهدف
fig, ax = plt.subplots(figsize=(9, 3.2))
for i, (label, r) in enumerate(out.iterrows()):
    ax.errorbar(r["الفرق"], i, xerr=[[r["الفرق"] - r["أدنى 95%"]], [r["أعلى 95%"] - r["الفرق"]]],
                fmt="o", color=[ORANGE, NAVY][i], capsize=6, markersize=9)
ax.set_yticks(range(len(out)))
ax.set_yticklabels([ar(s) for s in out.index])
ax.axvline(0, color=GRAY, linewidth=1)
ax.axvline(CONFIG["mde_abs"] * 100, color=TEAL, linestyle="--", label=ar("الأثر المستهدف"))
ax.set_xlabel(ar("الأثر على نسبة الطلب (نقطة مئوية) مع فترة الثقة 95%"))
ax.set_title(ar("المقياس الرئيسي"))
ax.legend()
plt.tight_layout()
plt.savefig(CHARTS_DIR / "primary_effect.png", dpi=120)
plt.close()

# ---- 7.2 المقاييس الثانوية، مع تصحيح الاختبارات المتعددة ----
A_orders, B_orders = A[A.ordered == 1], B[B.ordered == 1]
secondary = {
    "قيمة الطلب (لمن طلب)": diff_ci(A_orders["order_value"], B_orders["order_value"]),
    "الإيراد لكل مستخدم": diff_ci(A["revenue"], B["revenue"]),
    "نسبة الطلبات 100 ريال فأكثر": diff_ci(A_orders["order_value"] >= 100, B_orders["order_value"] >= 100),
}
sec = pd.DataFrame(secondary).T
sec["دال بعد تصحيح BH"] = multipletests(sec["p"].astype(float), alpha=0.05, method="fdr_bh")[0]
print(sec.round(3))
sec.round(4).to_csv(RESULTS_DIR / "secondary_metrics.csv", encoding="utf-8-sig")

# ---- 7.3 مقاييس الحماية ----
guardrail_defs = {                       # العمود: (الاسم، والاتجاه السيئ)
    "profit": ("الربح لكل مستخدم", "down"),
    "cancelled": ("نسبة إلغاء الطلبات", "up"),
    "contacted_support": ("التواصل مع الدعم", "up"),
}
rows, guard_status = [], {}
for col, (label, bad) in guardrail_defs.items():
    res = diff_ci(A[col].dropna(), B[col].dropna())
    if bad == "down":
        harmful, worse = res["أعلى 95%"] < 0, res["الفرق"] < 0
    else:
        harmful, worse = res["أدنى 95%"] > 0, res["الفرق"] > 0
    status = "تدهور دال" if harmful else ("تحذير" if (worse and res["p"] < 0.20) else "سليم")
    guard_status[label] = status
    rows.append({"المقياس": label, "A": A[col].mean(), "B": B[col].mean(), **res, "الحالة": status})
guard_table = pd.DataFrame(rows).set_index("المقياس")
print(guard_table.round(4))
guard_table.round(4).to_csv(RESULTS_DIR / "guardrails.csv", encoding="utf-8-sig")

# ---- 7.4 فحص أثر الحداثة ----
daily = data.groupby(["day", "variant"])["ordered"].mean().unstack()
daily_lift = (daily["B"] - daily["A"]) * 100
plt.plot(daily_lift.index, daily_lift.values, marker="o", color=TEAL, label=ar("الأثر في كل يوم"))
plt.axhline(primary["الفرق"] * 100, color=ORANGE, linestyle="--", label=ar("الأثر الكلي"))
plt.axhline(0, color=GRAY, linewidth=0.8)
plt.xlabel(ar("يوم دخول المستخدم"))
plt.ylabel(ar("الأثر (نقطة مئوية)"))
plt.title(ar("هل الأثر ثابت مع الوقت؟"))
plt.legend()
plt.savefig(CHARTS_DIR / "novelty_check.png", dpi=120)
plt.close()


# ======================== 8. التقرير والتوصية ========================
annual_users = CONFIG["daily_new_users"] * 365      # من بيانات المشروع بدل رقم ثابت


def decide_v2(diff, ci_low, ci_high, mde, guard_status):
    """قاعدة قرار تأخذ في الاعتبار الحد المجدي تجاريًا وحالة التحذير."""
    statuses = list(guard_status.values())
    if ci_high < 0:
        return "لا نطلق، لأن النسخة الجديدة أضرت بالمقياس الرئيسي."
    if "تدهور دال" in statuses:
        return "لا نطلق الآن، لأن أحد مقاييس الحماية ساء بشكل دال."
    if ci_low > 0 and diff < mde:
        return "الأثر إيجابي لكنه أصغر من الحد المجدي تجاريًا، فلا نطلق بصيغته الحالية."
    if ci_low > 0 and "تحذير" in statuses:
        return "الأثر على الطلب إيجابي، لكن أحد مقاييس الحماية يتجه سلبًا. لا نطلق للجميع قبل تجربة تركز على الربحية."
    if ci_low > 0:
        return "نطلق، لأن الأثر إيجابي بثقة ومقاييس الحماية سليمة."
    if ci_high < mde:
        return "لا نطلق، لأننا استبعدنا وجود أثر بالحجم الذي يهمنا."
    return "لا نقرر بعد. نمدد التجربة، أو نعيد تصميمها بقوة أعلى."


decision = decide_v2(primary["الفرق"], primary["أدنى 95%"], primary["أعلى 95%"], CONFIG["mde_abs"], guard_status)
profit = guard_table.loc["الربح لكل مستخدم"]
guard_rows = "\n".join(f"| {k} | {v} |" for k, v in guard_status.items())

report = f"""
<div dir="rtl">

### تقرير التجربة: {CONFIG['project']}

**القرار:** {decision}

| البند | القيمة |
|---|---|
| المقياس الرئيسي | نسبة الطلب من {A['ordered'].mean():.2%} إلى {B['ordered'].mean():.2%} |
| الأثر | {primary['الفرق'] * 100:.2f} نقطة (فترة الثقة 95%: من {primary['أدنى 95%'] * 100:.2f} إلى {primary['أعلى 95%'] * 100:.2f}) |
| الأثر مع CUPED | {primary_cuped['الفرق'] * 100:.2f} نقطة (من {primary_cuped['أدنى 95%'] * 100:.2f} إلى {primary_cuped['أعلى 95%'] * 100:.2f}) |
| التغير في قيمة الطلب | {sec.loc['قيمة الطلب (لمن طلب)', 'الفرق']:.2f} ريال |
| التغير التقديري في الربح السنوي | {profit['الفرق'] * annual_users / 1e6:.2f} مليون ريال (من {profit['أدنى 95%'] * annual_users / 1e6:.2f} إلى {profit['أعلى 95%'] * annual_users / 1e6:.2f}) |

| مقياس الحماية | الحالة |
|---|---|
{guard_rows}

</div>
"""
display(Markdown(report))
(RESULTS_DIR / "report.md").write_text(report, encoding="utf-8")
say("حُفظ التقرير في outputs/results/report.md والرسوم في outputs/charts")
