# قرار (Qrar) — AI Data Analyst for Power BI

منصة ذكاء اصطناعي مبنية بـ Streamlit تحوّل أسئلة المستخدم بالعربية/الإنجليزية إلى
استعلامات DAX تُنفَّذ مباشرة داخل نموذج Power BI مفتوح محلياً، عبر خادم
`powerbi-modeling-mcp` باستخدام بروتوكول MCP.

> **ملاحظة:** هذا سقالة (scaffold) كاملة تم بناؤها من الصفر حسب الوصف المعماري
> للمشروع (لم يكن هناك كود مصدري سابق في هذا المستودع). أسماء الأدوات (tools)
> التي يعرضها `powerbi-modeling-mcp.exe` الحقيقي قد تختلف عن الأسماء الافتراضية
> هنا — راجع قسم "التحقق من أدوات MCP" أدناه لضبطها.

## 1. هيكلة المشروع

```
qrar/
├── app.py                  # واجهة Streamlit الرئيسية (الشات)
├── config.py               # كل الإعدادات والمسارات (مطلقة عبر __file__)
├── requirements.txt
├── .env.example            # انسخه إلى .env واملأه
├── core/
│   ├── ai_router.py        # التوجيه بين المزودين + Smart Fallback
│   ├── ai_providers.py     # Ollama / OpenAI / Gemini + استخراج JSON آمن
│   ├── mcp_client.py       # عميل MCP عبر stdio (JSON-RPC 2.0)
│   └── chat_store.py       # حفظ/تحميل المحادثات كملفات JSON
├── chats/                  # يُنشأ تلقائياً — يحفظ كل محادثة كملف JSON
├── assets/
│   └── logo.png            # ضع شعارك هنا (اختياري)
└── bin/
    └── powerbi-modeling-mcp.exe   # ضع الملف التنفيذي هنا (أو غيّر المسار في .env)
```

كل المسارات (`chats/`, `assets/logo.png`, `bin/...exe`) محسوبة في `config.py`
بالنسبة لموقع الملف نفسه (`Path(__file__).resolve().parent`)، وليس بالنسبة
لمجلد العمل الحالي (`cwd`). هذا يحل أكثر مشكلة شائعة عند تشغيل مشاريع
Streamlit من مسارات مختلفة: لا يهم من أين تُشغّل `streamlit run`، ستُحل
المسارات دائماً بشكل صحيح.

## 2. خطوات التشغيل

### أ. تجهيز البيئة

```bash
python -m venv .venv
# ويندوز:
.venv\Scripts\activate
# لينكس/ماك:
source .venv/bin/activate

pip install -r requirements.txt
```

يتطلب المشروع Python 3.10 أو أحدث (يستخدم صياغة type hints مثل `dict | None`).

### ب. الإعدادات

```bash
cp .env.example .env
```

عدّل `.env`:
- `POWERBI_MCP_PATH`: المسار الكامل لملف `powerbi-modeling-mcp.exe`.
- `MCP_SCHEMA_TOOL` و `MCP_DAX_TOOL`: أسماء الأدوات الحقيقية (انظر القسم التالي).
- بيانات `OPENAI_API_KEY` / `GEMINI_API_KEY` إذا أردت تفعيل المزودين السحابيين.

### ج. تشغيل Ollama (التشغيل المحلي المجاني)

```bash
ollama serve
ollama pull llama3
```

تأكد أن `OLLAMA_BASE_URL` في `.env` يطابق عنوان الخادم (الافتراضي
`http://localhost:11434`).

### د. تشغيل Power BI Desktop

افتح ملف الـ `.pbix` في Power BI Desktop، ثم تأكد أن `powerbi-modeling-mcp.exe`
يمكنه الاتصال بمثيل Power BI المفتوح (حسب توثيق الأداة نفسها).

### هـ. تشغيل التطبيق

```bash
streamlit run app.py
```

### التحقق من أدوات MCP

بما أن أسماء الأدوات الفعلية تعتمد على إصدار `powerbi-modeling-mcp.exe`،
أضِف زر تشخيص مؤقت أو استخدم من الطرفية:

```python
from core.powerbi import PowerBIConnector
c = PowerBIConnector()
print(c.list_available_tools())
```

وحدّث `MCP_SCHEMA_TOOL` / `MCP_DAX_TOOL` في `.env` لتطابق الأسماء الظاهرة.

## 3. قرارات التصميم (لتفادي الأخطاء الشائعة)

طُلب الانتباه بشكل خاص لثلاث نقاط تسبب أخطاء متكررة في مشاريع من هذا النوع؛
هذا كيف تم التعامل معها هنا:

**أ. معالجة JSON من مخرجات LLM**
النماذج غالباً تُرجع JSON ملفوفاً بـ ```json ... ``` أو مع نص إضافي حوله.
`core/ai_providers._extract_json` يحاول استخراج أول كتلة `{...}` (سواء داخل
fence أو لا) قبل `json.loads`، ويرمي `ProviderError` بدلاً من `KeyError`/
`JSONDecodeError` خام إذا فشل — مما يسمح لـ `ai_router` بالانتقال تلقائياً
للمزود التالي بدل تعطّل الطلب بالكامل.

**ب. subprocess (الاتصال بـ MCP)**
- العملية الفرعية (`powerbi-modeling-mcp.exe`) تُنشأ **مرة واحدة فقط** لكل
  جلسة عبر `@st.cache_resource` على `PowerBIConnector` — بدون هذا، كل
  إعادة تشغيل لسكربت Streamlit (تحدث مع كل تفاعل) كانت ستُطلق عملية جديدة.
- كل طلب له `timeout` صريح (`MCP_REQUEST_TIMEOUT`)، فلا يتجمّد التطبيق إذا لم
  يستجب الخادم.
- قراءة `stderr` تتم في خيط منفصل بشكل مستمر لتفادي انسداد الأنابيب
  (pipe deadlock) الذي يحدث عند امتلاء بافر stderr بدون قراءة.

**ج. Threads و Streamlit session_state**
Streamlit لا يضمن أمان `st.session_state` عند الكتابة إليه من خيط غير الخيط
الرئيسي للسكربت. لذلك تصميم `MCPClient` هنا يُبقي كل الخيوط الخلفية (قارئ
stdout وقارئ stderr) **داخلية بالكامل**: هي فقط تملأ قاموس نتائج محمي بـ
`threading.Lock`، بينما الخيط الرئيسي (الذي يُشغّل `app.py`) هو الوحيد الذي
يستدعي `call_tool(...)` بشكل متزامن (blocking) وينتظر النتيجة عبر
`threading.Event`. النتيجة: لا حاجة لأي خيوط إضافية داخل `app.py` نفسه، ولا
أي كتابة على `st.session_state` من خارج الخيط الرئيسي.

## 4. حفظ المحادثات

كل محادثة تُحفظ كملف JSON مستقل في `chats/` باسم معرّف عشوائي (UUID). الكتابة
تتم بشكل ذرّي (atomic): تُكتب البيانات أولاً إلى ملف `.tmp` ثم يُستبدل الملف
النهائي عبر `os.replace` (ذرّي على ويندوز ولينكس)، لضمان عدم تلف الملف إذا
انقطع التطبيق أثناء الحفظ. القراءة أيضاً محمية: أي ملف تالف أو غير صالح
JSON يُتجاهل بدل تعطيل التطبيق بالكامل.

## 5. الشعار (logo.png)

ضع صورة باسم `logo.png` داخل `assets/`. إن لم تكن موجودة، تُخفى الصورة تلقائياً
من الشريط الجانبي (`config.LOGO_PATH.exists()`) بدل رمي خطأ.
