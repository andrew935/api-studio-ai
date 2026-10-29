# התקדמות מאומתת — API Studio AI

תאריך עדכון אחרון: 2026-10-28.

## מצב הלמידה

- שבוע נוכחי: **שבוע 2 — אינטגרציה עם LLM API**.
- יעד חיזוק שהושלם: **יום 5 — Pandas, NumPy ומבחן חוזר**. המשתמש יצר
  `DataFrame`, ניקה ערכי `NaN` ומחרוזות ריקות, הפיק ספירות באמצעות
  `value_counts().to_dict()`, וחישב ממוצע, סינון בוליאני וספירה במערך
  NumPy. נדרשה הכוונה בדיוק שמות המתודות ובתחביר הסינון.
- תוצאת המבחן החוזר ב־2026-10-28: **6.25/10**. ניכרת התקדמות לעומת
  4/10, אך היעד 8/10 טרם הושג. נקודות החיזוק הפעילות הן בניית מילון
  ספירה באופן עצמאי, `pytest.raises`, חריגות מדויקות ודיוק תחבירי
  ב־Pandas/NumPy. לבקשת המשתמש ממשיכים כעת בשבוע 2, וחוזרים לחיזוק
  Python ולמבחן קצר נוסף ב־2026-11-04.
- יעד פעיל כעת: **מדיניות timeout ו־retries של OpenAI SDK**. בקוד הקיים
  `create_openai_client()` מקבלת `timeout` ו־`max_retries`, אך אינה
  מעבירה אותם אל `AsyncOpenAI()`, ולכן הפרמטרים כרגע אינם משפיעים.
- יעד שהושלם: **הגדרת timeout ו־retries בפועל**. המשתמש העביר נכון את
  שני הערכים כ־keyword arguments אל `AsyncOpenAI`. הפתרון הוחל בקוד
  ונוספה בדיקת mock שמוודאת את האפשרויות ללא API key וללא רשת.
- אימות ממוקד ב־2026-10-29: **1 passed in 2.36s**. הרצת הסוויטה המלאה
  נתקעה ללא פלט בסביבת ההרצה והופסקה, ולכן אין לטעון שכל הסוויטה עברה
  לאחר השינוי הזה.
- יעד פעיל הבא: **tool calling בסיסי** — ההבדל בין תשובה טקסטואלית לבין
  בקשת המודל להפעיל פונקציה שהאפליקציה הגדירה והרשתה במפורש.
- ב־2026-10-28 התקבל מבחן אבחון Python בציון **4/10**. הממצאים מצביעים
  על צורך בחיזוק מעשי ב־dictionaries ולולאות, בניית אובייקטים ו־dataclasses,
  טיפול בנתונים חסרים, JSON וחריגות, וכתיבת בדיקות pytest. נושא ה־LLM
  מושהה זמנית עד להשלמת החיזוק; היעד הפעיל הוא יום 1 — dictionaries,
  loops ו־`get()`.
- יעד חיזוק שהושלם: **יום 1 — dictionaries, loops ו־`get()`**. המשתמש
  כתב `count_leads_by_source()`, השתמש ב־`get()` גם לברירת המחדל של
  המקור וגם לאתחול המונה, והבחין נכון בין מפתח חסר לערך ריק. הפונקציה
  המעודכנת ממפה מפתח חסר, `None` או מחרוזת ריקה ל־`unknown`.
- יעד פעיל הבא: יום 2 — `@dataclass`, יצירת אובייקט ו־`__post_init__`.
- יעד חיזוק שהושלם: **יום 2 — `@dataclass` ו־`__post_init__`**.
  המשתמש הגדיר `Lead` עם שדות וערך ברירת מחדל, יצר instance, נרמל שם
  ואימייל והוסיף `ValueError` לשם ריק ולאימייל ללא `@`. נדרש חיזוק מתמשך
  בדיוק תחבירי ובהזחות, אך הלוגיקה והזרימה הובנו.
- יעד פעיל הבא: יום 3 — JSON, חריגות וטעינת אובייקטים.
- יעד חיזוק שהושלם: **יום 3 — JSON, חריגות וטעינת אובייקטים**.
  המשתמש כתב את הלוגיקה של `load_leads(data)`: פענוח באמצעות
  `json.loads`, טיפול ב־`JSONDecodeError`, יצירת `Lead(**item)`, הוספה
  לרשימה ודילוג על רשומות שמעלות `ValueError` או `TypeError`. המשתמש
  הסביר נכון שרשומה שגויה אחת נזרקת בעוד הלולאה ממשיכה לרשומות הבאות.
  יש להמשיך לחזק הזחה עקבית עם רווחים במקום Tabs.
- יעד פעיל הבא: יום 4 — בדיקות `pytest` עם `assert`, ‏`pytest.raises`
  ו־`parametrize`.
- יעד חיזוק שהושלם: **יום 4 — בדיקות pytest**. המשתמש כתב assertions
  עבור נרמול שדות, בנה בדיקת `pytest.raises(ValueError)` והשתמש
  ב־`@pytest.mark.parametrize` לשלושה אימיילים פסולים. לאחר שהלוגיקה
  נכתבה על ידו, קובצי התרגול הישנים תוקנו ונוספו בדיקות מקומיות עבור
  `Lead`, ‏`load_leads` וספירת מקורות.
- אימות בפועל ב־2026-10-28: **41 passed in 5.01s**. כל הבדיקות מקומיות;
  לא בוצעו קריאות אינטרנט או OpenAI.
- יעד פעיל הבא: יום 5 — NumPy/Pandas, חזרה ומבחן חוזר.
- יעד שהושלם כעת: **יסודות Python async / await**.
- המשתמש ניסה את תרגיל `fetch_demo_user_count()`, קיבל תיקון מודרך
  והסביר נכון שללא `await` לא מתקבלת התוצאה, ושבזמן המתנה ה־event loop
  יכול לקדם בקשה אחרת.
- נקודות לחיזוק: ההבדל בין פונקציית module למתודה עם `self`, עבודה עם
  dictionaries לעומת object properties, ושימוש ב־`len()` במקום `count()`.
- שבוע 2, React ופיצ׳רי AI טרם התחילו.
- יעד שהושלם: **טיפול בסיסי בשגיאות עם `try` / `except` ו־HTTPX**.
- יעד שהושלם כעת: **Pydantic ו־FastAPI request validation**.
- יעד שהושלם כעת: **Dependency Injection בסיסי ב־FastAPI**.
- המשתמש שינה את `GET /api/v1/requests/test` כך שהתוצאה של
  `fetch_demo_users` מוזרקת באמצעות `Depends`, והבחין בקשר ל־service
  injection ב־Laravel.
- יעד שהושלם כעת: **חוזה החזרה עקבי בין פונקציות service**.
- המשתמש תיקן את `fetch_demo_user_count()` כך שהיא מזהה `error_type`,
  מחזירה שגיאה ללא שינוי וניגשת ל־`data` רק בתוצאת הצלחה.
- יעד שהושלם כעת: **fixture ו־assert בסיסיים ב־pytest**.
- המשתמש יצר fixture בשם `count_input`, הבין שההזרקה נעשית לפי שם
  הפרמטר, וכתב בדיקת Arrange/Act/Assert עבור `format_user_count()`.
- יעד שהושלם כעת: **mocking בסיסי באמצעות `monkeypatch`**.
- המשתמש כתב fake אסינכרוני שמקיים את חוזה `fetch_demo_users`, החליף את
  התלות בזמן הטסט וקרא ל־`fetch_demo_user_count()` עם `await`.
- יעד שהושלם כעת: **parametrization ב־pytest**.
- המשתמש החליף fixture יחידה בשלושה מקרי קלט עבור
  `format_user_count()` והשתמש בערכי הקלט גם בבניית התוצאה הצפויה.
- יעד שהושלם כעת: **יסודות class, instance, method ו־`self`**.
- המשתמש כתב `UserCounter`, שמר את רשימת המשתמשים ב־`self.users`, יצר
  instance והפעיל את `count()`; הובהר גם ההבדל בין method object לקריאה
  עם סוגריים ומוסכמות PascalCase/snake_case.
- יעד שהושלם כעת: **בחירה בין class לפונקציית module**.
- המשתמש זיהה ש־HTTP client עם `base_url`, token ו־timeout משותפים מתאים
  ל־class, משום שהמתודות חולקות state/configuration.
- יעד שהושלם כעת: **תרגום שגיאות service לתגובות HTTP ב־FastAPI**.
- המשתמש מיפה timeout ל־504 ושגיאת HTTP/חיבור ל־502 באמצעות
  `raise HTTPException`, והסביר את ההבדל בין status, headers ו־body.
- המשתמש עדכן טסט פרמטרי כך שיאמת בנפרד `ReadTimeout` ו־`ConnectError`.
  הרצת הטסט הממוקד נתקעה בזמן בקשת `TestClient` ולא הסתיימה; התהליך
  הופסק ולכן אין תוצאת pytest מאומתת עבור השינוי.
- יעד שהושלם כעת: **decorators בסיסיים ב־FastAPI וב־pytest**.
- המשתמש זיהה ש־`@router.get` רושם route, והובהר ש־prefix של ה־router
  משתתף בנתיב המלא. המשתמש הבדיל בין קוד האפליקציה לבין pytest, שבו
  `@pytest.mark.parametrize` מגדיר כמה מקרי קלט לאותה בדיקה.
- יעד שהושלם כעת: **virtual environment וניהול תלויות בסיסי**.
- המשתמש זיהה שכלי formatting שייך ל־`requirements-dev.txt` משום שאינו
  דרוש בזמן ריצה, והבדיל בין formatter, linter, type checker ו־pytest.
- המשתמש אישר להתחיל את שבוע 2.
- יעד פעיל: להבין את מבנה קריאת ה־LLM הראשונה דרך Responses API לפני
  הוספת SDK, credentials או קוד אינטגרציה לפרויקט.
- יעד שהושלם כעת: **מבנה קריאת Responses API אסינכרונית**.
- המשתמש זיהה ש־`responses.create()` היא הפעולה ששולחת את בקשת הרשת,
  הוסיף `await`, העביר `model` ו־`input`, והסביר ש־`output_text` מוחזר
  משום שחוזה הפונקציה הוא `-> str` ולא אובייקט response מלא.
- יעד פעיל הבא: authentication וניהול API key ללא חשיפת secret בקוד.
- יעד שהושלם כעת: **authentication בסיסי וניהול API key**.
- המשתמש בחר ב־`AsyncOpenAI()` ללא secret קשיח בקוד והסביר שהמפתח אינו
  חשוף שם; הובהר שה־SDK קורא את `OPENAI_API_KEY` מסביבת השרת בזמן ריצה.
- יעד פעיל הבא: ההבדל בין `instructions` לבין `input` בקריאת מודל.
- יעד שהושלם כעת: **`instructions` לעומת `input`**.
- המשתמש סיווג נכון כלל התנהגות קבוע כ־`instructions` ומשימה ספציפית
  כ־`input`.
- יעד שהושלם כעת: **tokens וחישוב עלות בסיסי**.
- המשתמש השתמש בנוסחת עלות לפי מיליון tokens; לאחר תיקון מחירי המודל
  חישבנו 1,000 input ו־1,000 output tokens ב־Astra בעלות כוללת של $0.06.
- יעד פעיל הבא: בחירת מודל לפי איכות, latency, תדירות ועלות.
- יעד שהושלם כעת: **בחירת מודל בסיסית**.
- המשתמש בחר ב־`gpt-6-luna` לסיווג 100,000 הודעות ביום משום שהמשימה
  ממוקדת והתדירות הגבוהה מחייבת עלות נמוכה; הובהר שיש לאמת איכות על
  dataset מייצג ולא להסתפק במחיר.
- יעד פעיל הבא: Structured Outputs עם מודל Pydantic.
- יעד שהושלם כעת: **Structured Outputs עם Pydantic**.
- המשתמש הגדיר `SupportClassification` עם קטגוריות `Literal`, confidence
  בטווח 0–1 ובכפולות של 0.01, ו־`needs_human_review` בוליאני.
- נוספה התשתית הראשונה לאינטגרציית LLM: `openai==3.37.0`, schema בקובץ
  `schemas/llm.py` ושירות אסינכרוני ב־`services/llm_client.py` המשתמש
  ב־`AsyncOpenAI.responses.parse()` וב־`gpt-6-luna`.
- ה־client מוזרק לפונקציית השירות, ולכן טסטים אינם דורשים API key ואינם
  מבצעים קריאת רשת. נוסף גם `.gitignore` שחוסם קובצי `.env`.
- אימות בפועל ב־2026-10-26: **25 passed in 3.49s**; ‏`pip check` החזיר
  `No broken requirements found.` לא בוצעה בדיקת OpenAI חיה ולא נצרכה עלות.
- יעד פעיל הבא: review של הזרקת OpenAI client והפרדת קריאה חיה מ־mock.
- נוסף `POST /api/v1/ai/classify` עם `SupportMessage` כקלט ו־
  `SupportClassification` כ־response model. ה־router נרשם ב־`main.py`.
- בדיקות ה־route משתמשות ב־`app.dependency_overrides` כדי להזריק fake
  client ולבדוק את הזרימה route → service → structured output ללא רשת.
- אימות בפועל לאחר הוספת ה־endpoint: **29 passed in 2.59s**;
  ‏`pip check` החזיר `No broken requirements found.`
- יעד פעיל הבא: להבין `dependency_overrides` ולאחר מכן לטפל בשגיאות SDK.
- יעד שהושלם כעת: **טיפול בשגיאות OpenAI SDK ברמת ה־route**.
- המשתמש כתב `try` / `except` עבור `APITimeoutError`,
  `APIConnectionError`, `RateLimitError` ו־`APIError`, שממופים בהתאמה
  ל־504, 502, 503 ו־500. הוא שמר על סדר מהחריגה הספציפית לכללית כדי
  ש־`APIError` לא יתפוס את כל המקרים קודם.
- נוספה בדיקה פרמטרית שמדמה את ארבע החריגות ללא רשת, API key או עלות.
- אימות בפועל ב־2026-10-26: **33 passed in 1.99s**.
- יעד פעיל הבא: להבין את מדיניות ה־retries וה־timeout של OpenAI SDK.
- המשתמש הבין ש־`max_retries` סופר ניסיונות חוזרים בלבד: ערך `2` מאפשר
  עד שלושה ניסיונות בסך הכול, וערך `0` משאיר ניסיון יחיד ללא retry.

## מה נמצא לפני השינוי

- נקרא מסמך ההעברה שסופק מתוך Downloads, ונבדקו קובצי הפרויקט בפועל.
- כל קוד האפליקציה היה ב־`backend/app/main.py`: מודל Pydantic, שלושה
  endpoints וקריאת HTTPX אחת.
- סביבת `backend/.venv` קיימת, עם Python 3.12.10.
- `frontend/` קיימת וריקה. לא נמצאו בדיקות או קובצי תלויות לפרויקט.
- בזמן הבדיקה תיקיית הפרויקט לא הייתה מאגר Git; לא נוצר מאגר חדש.

## נושאים שנחשפו עד כה

- מבנה חבילות ומודולים ב־Python.
- הפרדת אחריות בין FastAPI app, routers, schemas ו־services.
- Pydantic model בסיסי ו־validation של FastAPI.
- HTTPX `AsyncClient`, `async def`, `await` ו־`async with` קיימים בקוד.
- בדיקות routes עם pytest, fixtures, parametrization ו־MockTransport.

הרשימה מתארת קוד שנבדק ונושאים שנחשפו. היא אינה מעידה לבדה שהמשתמש
כבר תרגל או שולט בכל המושגים.

## מה השתנה ולמה

- `main.py` יוצר את אפליקציית FastAPI ורושם routers בלבד.
- `api/routes/root.py` מכיל את דף הבית; `api/routes/requests.py` מכיל
  את נתיבי הבקשות. Router הוא אוסף של נתיבים שמחברים לאפליקציה.
- `schemas/requests.py` מכיל את `APIRequest`. מחלקה שיורשת מ־Pydantic
  `BaseModel` מתארת את שדות הקלט ומאפשרת ל־FastAPI לבדוק אותם.
  `url: str` ו־`method: str` נשארו מחרוזות, בדיוק כמו בקוד המקורי.
- `services/http_client.py` מכיל את `fetch_demo_users` ואת כל קוד HTTPX.
  הנתיב מקבל את תוצאת השירות באמצעות `Depends`; FastAPI ממתין לתלות
  האסינכרונית. `async with` דואג לסגירת לקוח ה־HTTP גם במקרה של שגיאה.
- קובצי `__init__.py` הריקים הוסרו לבקשת המשתמש. הפרויקט משתמש כעת
  ב־implicit namespace packages של Python 3.12; imports ורישום התלות
  ב־FastAPI אומתו לאחר ההסרה.
- נוספו בדיקות רגרסיה, `pytest.ini`, קובצי תלויות ו־`AGENTS.md`/`TASKS.md`.
  תלויות הריצה נרשמו בגרסאות שכבר היו מותקנות; pytest 9.1.1 נוסף לבדיקות.

מסלול בקשת ההדגמה:

```text
GET /api/v1/requests/test
  -> api/routes/requests.py
  -> services/http_client.py: fetch_demo_users()
  -> HTTPX -> https://jsonplaceholder.typicode.com/users
  -> JSON response
```

ההפרדה מצמצמת את האחריות של כל קובץ ומאפשרת לשנות או לבדוק את שירות
הרשת בנפרד מהגדרת הנתיבים, בלי להוסיף כרגע שכבות שאינן נחוצות.

## התנהגות קיימת שנשמרה

| נתיב | התנהגות |
| --- | --- |
| `GET /` | מחזיר `{"message":"Welcome to API Studio AI"}` |
| `POST /api/v1/requests/preview` | מקבל `url` ו־`method` ומחזיר אותם עם `status: ready`; אינו שולח HTTP |
| `GET /api/v1/requests/test` | מבצע GET לכתובת ההדגמה הקבועה ומחזיר `status_code` ו־`data` |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | מפרט OpenAPI של האפליקציה |

נשמרו timeout של 10 שניות והטיפול ב־`httpx.HTTPError`; מבנה השגיאה שונה
בתרגיל ל־`error_type` ו־`message`. במקרה זה התשובה של FastAPI עדיין HTTP 200.
לא הוחמר אימות הקלט ולא נוספו שדות או יכולות שליחת בקשות דינמיות.

## מבנה מעודכן

```text
api-studio-ai/
|-- AGENTS.md
|-- TASKS.md
|-- PROGRESS.md
|-- pytest.ini
|-- backend/
|   |-- requirements.txt
|   |-- requirements-dev.txt
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |   `-- routes/
|   |   |       |-- root.py
|   |   |       `-- requests.py
|   |   |-- schemas/
|   |   |   `-- requests.py
|   |   `-- services/
|   |       `-- http_client.py
|   `-- tests/
|       `-- test_routes.py
`-- frontend/  (empty)
```

התיקיות הקיימות `.serena/`, `backend/.venv/` ומטמוני Python/pytest
הושמטו מהתרשים לצורך קריאות.

## הרצה ובדיקה ב־PowerShell

מריצים משורש הפרויקט: `C:\Users\a0546\Documents\projects_py\api-studio-ai`.
הפקודות משתמשות ישירות בסביבה הווירטואלית; אין צורך להפעיל `Activate.ps1`.

התקנת תלויות ריצה ובדיקות:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

הפעלת שרת פיתוח:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

פותחים `http://127.0.0.1:8000/docs` לבדיקה ידנית. ניתן לנסות את preview עם:

```json
{"url": "https://jsonplaceholder.typicode.com/users", "method": "GET"}
```

preview רק מחזיר את הקלט. הפעלת `GET /api/v1/requests/test` שולחת את
בקשת ההדגמה הקבועה ודורשת גישה לאינטרנט. עוצרים את השרת עם `Ctrl+C`.

הרצת הבדיקות האוטומטיות ובדיקת עקביות התלויות:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -q
.\backend\.venv\Scripts\python.exe -m pip check
```

## תוצאות שהתקבלו בפועל

- לפני הפיצול: **18 עברו, 0 נכשלו**.
- לאחר הפיצול: **18 עברו, 0 נכשלו**, ב־0.98 שניות.
- הכיסוי כולל: דף הבית, preview עבור חמש השיטות המתוכננות, שמירת שדות
  מחרוזת ללא החמרת ולידציה, קלט לא תקין עם 422, תשובת הדגמה מוצלחת,
  שגיאות upstream של 404/500, timeout ושגיאת חיבור, Swagger ו־OpenAPI.
- הבדיקות משתמשות ב־`httpx.MockTransport`; אינן תלויות בשרת חיצוני.
  נבדקים גם כתובת ההדגמה הקבועה, שיטת GET ו־timeout של 10 שניות.
- אזהרה אחת, שהופיעה לפני הפיצול וגם אחריו: `StarletteDeprecationWarning`
  על שימוש ב־HTTPX בתוך TestClient. לא שונו תלויות הריצה לטיפול באזהרה.
- `pip check`: `No broken requirements found.`
- בדיקה חיה נפרדת: הופעל שרת Uvicorn זמני על loopback בלבד. דף הבית,
  preview, `/docs` ו־`/openapi.json` החזירו 200. גם נתיב ההדגמה החזיר 200,
  עם `status_code: 200` מהשירות החיצוני ו־10 משתמשים.
- שרת האימות הזמני הופסק בסיום; לא הושאר שרת רץ.

## אימות מסכם — 2026-10-26

- Starlette 1.9.0 משתמשת ב־`httpx2` עבור `TestClient`; נוספה
  `httpx2==2.16.0` לתלויות הפיתוח, בעוד קוד ה־service ממשיך להשתמש
  ב־`httpx==0.28.1` כתלות runtime.
- טסטים ישנים סונכרנו עם חוזה השגיאות החדש: timeout מחזיר 504 ושגיאת
  upstream מחזירה 502, עם גוף `detail` של `HTTPException`.
- קובץ תרגול שנשאר בו קוד לא תקין נוקה לטסט ממוקד של
  `fetch_demo_user_count()`.
- בתוך ה־sandbox גם event loop מינימלי של `asyncio` נתקע; לכן האימות
  המסכם הורץ מחוץ ל־sandbox, ללא HTTP חי ובאמצעות mocks.
- `pytest`: **22 passed, 0 failed** בזמן 0.79 שניות.
- `pip check`: **No broken requirements found.**

## אימות חוזר — 2026-10-21

- `pytest`: **18 passed, 0 failed** בזמן 0.70 שניות.
- התקבלה שוב אזהרת `StarletteDeprecationWarning` יחידה מתוך TestClient;
  היא אינה כשל ואינה מצדיקה שינוי תלויות במסגרת המשימה הנוכחית.
- smoke test דרך שרת Uvicorn זמני עבר:
  - `GET /` החזיר 200 ואת הודעת הפתיחה.
  - `POST /api/v1/requests/preview` החזיר 200 ואת הקלט עם `status: ready`.
  - `GET /api/v1/requests/test` החזיר 200, וה־upstream החזיר 200 ו־10 רשומות.
  - `GET /docs` החזיר 200.
- שרת הבדיקה הזמני הופסק. לא נדרש תיקון קוד לשחזור פונקציונליות.

## החלטות טכניות חשובות

- נשמרה הארכיטקטורה הקיימת: router מטפל ב־HTTP, schema בקלט, service
  בתקשורת החיצונית ו־main ברישום האפליקציה.
- `fetch_demo_users()` נשאר async משום שהוא ממתין ל־network I/O.
- `preview_request()` נשאר sync משום שאינו מבצע כרגע I/O אסינכרוני.
- בדיקות אוטומטיות ממשיכות להשתמש ב־mock; בדיקה חיה מתועדת בנפרד.

## תרגילים והבנה

- תרגיל `fetch_demo_user_count()` — הוגש ניסיון ונעשה review.
- המשתמש זיהה לאחר ההסבר שקריאה ל־coroutine ללא `await` אינה מספקת את
  תוצאת ה־dictionary.
- המשתמש הסביר נכון שבזמן network I/O ה־event loop יכול לטפל בבקשה אחרת.
- סטטוס: יסודות `async/await` הושלמו; יש לחזק את תחביר Python בתרגילים
  הבאים בלי לחזור על התאוריה כולה.
- תרגיל exceptions — המשתמש כתב טיפול נפרד ב־`TimeoutException`,
  `RequestError` ו־`Exception`. ב־review תוקן הבלוק הכללי ל־`HTTPError`
  כדי לכלול גם `HTTPStatusError`, והוסר `Exception` הרחב מדי. המשתמש אישר
  להמשיך לנושא הבא.
- תרגיל type hints — המשתמש כתב חתימה נכונה עבור `format_user_count`,
  כולל טיפוסי פרמטרים, טיפוס החזרה ו־union בתוך dictionary. הובהר ש־type
  hints הם בעיקר מידע לכלי פיתוח, אך FastAPI/Pydantic משתמשים בהם גם בזמן
  ריצה לצורך validation ו־OpenAPI.
- תרגיל Pydantic — המשתמש כתב נכון מודל `UserRequest` עם שני שדות חובה
  (`name`, `age`) ושדה `active` עם ברירת מחדל `True`.
- תרגיל Dependency Injection — המשתמש החליף קריאה ישירה ל־service
  ב־`Depends(fetch_demo_users)`. לאחר תיקון מודרך, ה־route מקבל את תוצאת
  התלות דרך הפרמטר `result`; FastAPI מבצע את הקריאה האסינכרונית.
- תרגיל חוזה החזרה — המשתמש תיקן את בדיקת השגיאה מ־`error` ל־`error_type`.
  שתי הזרימות אומתו ישירות עם dependency מדומה: הצלחה החזירה count של 2,
  ושגיאת timeout הוחזרה כאותו object ללא שינוי. pytest לא אומת, משום שגם
  event loop מינימלי נתקע בסביבת ההרצה הנוכחית.
- תרגיל fixture — המשתמש יצר `count_input`, העביר אותו לטסט באמצעות שם
  הפרמטר ובדק את התוצאה עם `assert`. הטסט הסינכרוני הורץ בפועל ב־2026-10-25:
  **1 passed in 0.17s**.
- תרגיל mocking — המשתמש כתב `fake_fetch_demo_users`, חיבר אותו עם
  `monkeypatch` והסביר נכון ששתי רשומות ב־`data` צריכות להפיק count של 2.
  קובץ הטסט מתקמפל ו־pytest אוסף טסט asyncio אחד; הרצת הטסט לא הושלמה
  משום שיצירת event loop נתקעת בסביבת הכלי הנוכחית.
- תרגיל parametrization — המשתמש הגדיר שלושה tuples של `count` ו־`label`
  עבור אותו טסט. הקוד נשמר והורץ בפועל ב־2026-10-25:
  **3 passed in 0.32s**.
- תרגיל class — המשתמש הגדיר constructor עם `self.users`, מתודת `count`
  ויצירת instance עבור שלושה משתמשים. לאחר תיקון מודרך הובהר ש־`len` היא
  פונקציה מובנית ושמתודה מופעלת באמצעות סוגריים.
- תרגיל `HTTPException` — המשתמש עדכן את route ההדגמה כך ש־timeout מעלה
  504 ושגיאת upstream מעלה 502, ועדכן parametrization עם ה־status הצפוי.
  הובהר ש־`raise` עוצר את ה־route ו־FastAPI ממירה את החריגה לתגובה, בעוד
  `return` של מילון משתמש כברירת מחדל ב־200. הקוד נשמר ואומת במסגרת
  הסוויטה המסכמת: 22 בדיקות עברו.

## נקודת עצירה

שבוע 1 הושלם ואומת. תורגלו יסודות
`async/await`, טיפול בשגיאות, type hints, Pydantic, dependency injection,
pytest, classes, decorators, סביבות ותלויות, ותרגום שגיאות service ל־HTTP
באמצעות `HTTPException`. ממתינים לאישור המשתמש לעבור לשבוע 2.
