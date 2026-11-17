import re

# 1. نقرأ الكود القديم
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 2. نضيف الاستيرادات فوق
imports = "from render_engine import render_with_format\nfrom campaign_ai import analyze_campaign\nfrom scheduler import add_to_schedule, start_scheduler\n"
if "from render_engine import" not in code:
    code = imports + code

# 3. ندور على دالة الرندر القديمة ونستبدلها
if "render_video(" in code:
    code = code.replace("render_video(", "render_with_format(")

# 4. نحفظ الملف
with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("app.py updated successfully!")