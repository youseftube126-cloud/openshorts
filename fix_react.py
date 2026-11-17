import os

file_path = "dashboard/src/App.jsx"

if not os.path.exists(file_path):
    print("Error: App.jsx not found!")
    exit()

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. إضافة الـ States
target1 = "const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_key') || '');"
replacement1 = target1 + "\n  const [formatId, setFormatId] = useState('podcast_vertical');\n  const [campaignData, setCampaignData] = useState(null);"
if target1 in content:
    content = content.replace(target1, replacement1)
    print("✅ Added States.")
else:
    print("⚠️ State target not found. (Already added?)")

# 2. ربط الفورمات بالـ API
target2 = "const advanced = {"
replacement2 = target2 + "\n        format_id: formatId,"
if target2 in content:
    content = content.replace(target2, replacement2)
    print("✅ Added formatId to API payload.")
else:
    print("⚠️ API target not found. (Already added?)")

# 3. إضافة زراير الفورمات في الواجهة
target3 = "<MediaInput onProcess={handleProcess} isProcessing={status === 'processing'} />"
replacement3 = target3 + """
                <div className="mt-6 max-w-xl mx-auto w-full">
                  <FormatSelector selected={formatId} onSelect={setFormatId} />
                  <CampaignWizard onAnalyze={(data) => setCampaignData(data)} />
                </div>"""
if target3 in content:
    content = content.replace(target3, replacement3)
    print("✅ Added UI components.")
else:
    print("⚠️ UI target not found. (Already added?)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("🎉 App.jsx has been updated successfully!")