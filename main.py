"""المشروع الختامي: التوصيل المجاني للطلبات فوق 100 ريال
برنامج التجارب واختبارات A/B والاستدلال السببي، أكاديمية سدايا

التشغيل:  python main.py
يشغّل الأجزاء الأربعة بالترتيب، لأن كل جزء يستورد الجزء الذي قبله:
  part1_tools.py               أدوات جاهزة
  part2_sample_size.py         3. حجم العينة والمدة
  part3_data_and_trust.py      5. إنشاء البيانات بالمحاكاة، و6. فحوص الثقة
  part4_analysis_and_report.py 7. التحليل، و8. التقرير والتوصية
"""
import matplotlib
matplotlib.use("Agg")   # حفظ الرسوم في ملفات بدل فتح نوافذ

import part4_analysis_and_report  # noqa: F401
