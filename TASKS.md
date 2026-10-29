# תוכנית ומשימות — API Studio AI

## מצב נוכחי

- שבוע נוכחי: **שבוע 2 — אינטגרציה עם LLM API**.
- יעד למידה פעיל: **שבוע 2 — timeout ו־retries ב־OpenAI SDK**.
- יש להמתין לניסיון המשתמש בתרגיל לפני סימון הנושא כהושלם.

## חיזוק Python לפני המשך שבוע 2

- [x] יום 1: פונקציות, dictionaries, loops ו־`get()`.
- [x] יום 2: `@dataclass`, בנאי ו־`__post_init__`.
- [x] יום 3: JSON, חריגות וטעינת אובייקטים.
- [x] יום 4: `assert`, ‏`pytest.raises` ו־`parametrize`.
- [x] יום 5: NumPy/Pandas, חזרה ומבחן חוזר של 10 נקודות.
- [ ] לחזור לחיזוק Python ולמבחן קצר נוסף ב־2026-11-04; יעד: לפחות 8/10.

## שבוע 1 — Python ו־FastAPI

יעדים: מבנה פרויקט Python, classes, type hints, Pydantic, FastAPI,
routes, services, dependency injection בסיסי, async/await, exceptions,
virtual environments, HTTPX ו־pytest.

משימות והתקדמות:

- [x] לבדוק את הפרויקט וה־endpoints הקיימים.
- [x] להפריד את FastAPI ל־routes, schemas ו־services.
- [x] להשאיר את `main.py` מינימלי.
- [x] להוסיף בדיקות רגרסיה עם HTTP מדומה.
- [x] ליצור קובצי תלויות ו־`AGENTS.md`, `TASKS.md`, `PROGRESS.md`.
- [x] להריץ מחדש 18 בדיקות ולבצע smoke test חי ב־2026-10-21.
- [x] ללמוד את יסודות `async`, `await`, event loop ו־asynchronous I/O.
- [x] תרגיל: לזהות אילו פונקציות בזרימת בקשת ההדגמה צריכות להיות async
  ולהסביר היכן צריך `await` ומדוע.
- [x] לבדוק את פתרון התרגיל ולוודא הבנה בסיסית של `await` וה־event loop.
- [x] ללמוד `try`, `except`, סוגי exceptions והימנעות מ־`except` רחב מדי.
- [x] תרגיל: להוסיף טיפול נפרד ב־timeout ברמת פונקציית service לדוגמה.
- [x] לבדוק את פתרון תרגיל השגיאות ולוודא הבנה.
- [x] ללמוד type hints לפרמטרים, ערכי החזרה ו־containers.
- [x] לבצע תרגיל type hints קצר המבוסס על `format_user_count()`.
- [x] לבדוק את פתרון תרגיל ה־type hints ולוודא הבנה בסיסית.
- [x] להבין `BaseModel`, שדות חובה, coercion ושגיאת `422` ב־FastAPI.
- [x] לבצע תרגיל Pydantic קצר על מודל בקשה.
- [x] לבדוק את התרגיל ולוודא הבנה.
- [x] ללמוד Dependency Injection בסיסי עם `Depends` ב־FastAPI.
- [x] לבצע תרגיל הזרקת `fetch_demo_users` ל־route ולבדוק את הפתרון.
- [x] לתקן את חוזה ההחזרה בין `fetch_demo_users()` לבין
  `fetch_demo_user_count()`.
- [x] ללמוד fixture בסיסי ב־pytest ולכתוב בדיקה סינכרונית עם `assert`.
- [x] ללמוד mocking של service חיצוני בלי לבצע HTTP אמיתי.
- [x] ללמוד parametrization ולהריץ אותה בדיקה עם כמה מקרי קלט.
- [x] ללמוד class, constructor, instance, method ו־`self`.
- [x] לתרגל החלטה מתי class מוצדק ומתי פונקציה פשוטה עדיפה.
- [x] ללמוד כיצד `HTTPException` מתרגמת שגיאת service ל־HTTP status.
- [x] לתרגל מיפוי timeout ל־504 ושגיאת upstream ל־502 ולכתוב טסט פרמטרי.
- [x] להבין decorators בסיסיים של FastAPI ושל pytest.
- [x] להבין virtual environment והפרדה בין תלויות runtime לתלויות development.
- [x] להשלים את יעדי שבוע 1 ולבצע אימות מסכם של הקוד והבדיקות.

תוצאה מעשית רצויה: להבין כיצד backend מקצועי ב־Python בנוי ורץ, ולא רק
להחזיק בקוד שנוצר.

## שבוע 2 — אינטגרציה עם LLM API

יעדים: LLMs, model APIs, system/user prompts, tokens, בחירת מודל,
temperature, structured outputs, JSON, tool calling בסיסי, authentication
ובקרת עלויות.

- [x] לבנות שירות Python שמתקשר עם LLM ומחזיר תוצאה מובנית.
- [ ] להבין tool calling בסיסי: הגדרת tool, בחירת tool וביצוע מבוקר.
- [x] להתחיל רק לאחר אישור המשתמש.
- [x] להבין client, קריאת `responses.create`, קלט ופלט בסיסיים.
- [x] לתרגל קריאה אסינכרונית עם `AsyncOpenAI`, `await` ו־`output_text`.
- [x] להבין authentication בסיסי ושמירת API key במשתנה סביבה.
- [x] להבין את ההבדל בין `instructions` קבועות לבין `input` משתנה.
- [x] להבין input/output tokens ולחשב עלות בסיסית לפי מחיר למיליון tokens.
- [x] לבחור מודל התחלתי לפי מורכבות, תדירות, latency ועלות.
- [x] להגדיר Structured Output באמצעות Pydantic ו־constraints.
- [x] להוסיף OpenAI SDK ושירות סיווג אסינכרוני עם client מוזרק.
- [x] לבדוק את שירות ה־LLM באמצעות mock בלבד, ללא API חי או עלות.
- [x] לחשוף endpoint מסווג עם request/response models ו־OpenAI client מוזרק.
- [x] לבדוק את ה־endpoint באמצעות dependency override ללא רשת או עלות.
- [x] למפות שגיאות OpenAI SDK לתגובות HTTP ולבדוק אותן באמצעות mock.
- [x] להגדיר בפועל `timeout` ו־`max_retries` ב־`AsyncOpenAI` ולבדוק אותם.

## שבוע 3 — Agent מאפס

יעדים: ההבדל בין Agent לקריאת LLM, הגדרת tools, בחירת tool, execution
loop, תוצאות tools, שגיאות, execution limits ואישור אנושי.

- [ ] לבנות Agent ללא framework מלא: קבלת משימה, החלטה על tool, ביצוע,
  המשך לפי הצורך והחזרת תוצאה סופית.

## שבוע 4 — Frameworks ו־state

יעדים: OpenAI Agents SDK, יסודות LangGraph, state, memory, workflows,
human-in-the-loop, persistence ודיבוג Agents.

- [ ] לשפר את ה־Agent בעזרת framework מתאים ולהסביר מתי framework מועיל.
- [ ] להתחיל מחקר שוק עבודה, gap analysis, הכנה לראיונות ו־system design.
- [ ] להתחיל לחזק את תיק העבודות; חיפוש עבודה פעיל רק באישור מפורש.

## שבוע 5 — RAG, MCP ואינטגרציות

יעדים: embeddings, vector databases, עיבוד מסמכים, retrieval, MCP,
כלים חיצוניים, API integrations, authentication והרשאות.

- [ ] לבנות Agent שקורא תיעוד, מאחזר מידע רלוונטי ופועל מול APIs.

## שבוע 6 — Multi-Agent Systems

יעדים: orchestration, supervisor patterns, פירוק משימות, Manager,
Executor, Reviewer, evaluation, retries ובקרת עלויות.

- [ ] לבנות Manager/Executor/Reviewer רק אם ההפרדה נותנת ערך מדיד לעומת
  Agent יחיד.

## שבוע 7 — Production Engineering

יעדים: Docker, CI/CD, GitHub Actions, configuration, environment variables,
secrets, logging, monitoring, recovery, rate limits, API/Agent security,
מעקב עלויות, evaluation ובדיקות.

- [ ] להכין את אפליקציית ה־Agent לפריסה באופן מאובטח.

## שבוע 8 — פרויקט גמר והכנה לקריירה

יעדים: system design, ארכיטקטורת AI, תיעוד, trade-offs, הצגת portfolio
והכנה לראיונות Python, backend ו־AI Engineering.

- [ ] לבנות מערכת Agent שמקבלת משימה אמיתית, מתכננת, משתמשת בכלים,
  מטפלת בשגיאות, עוקבת אחר ביצוע, מעריכה תוצאה ומפיקה דוח מובנה.
- [ ] להכין את הפרויקט להצגה בתיק עבודות ובראיונות.

## אבני דרך מוצר עתידיות — אינן המשימה הנוכחית

- [ ] מנוע HTTP דינמי מאובטח עם מתודות, URL, headers/auth, query, JSON
  ותשובת status/headers/body/time, לאחר הגנות SSRF והרשאות.
- [ ] PostgreSQL, משתמשים, פרויקטים, collections והיסטוריה עם בידוד גישה.
- [ ] ממשק React ו־TypeScript.
- [ ] שיתוף והרשאות.
- [ ] קליטת PDF/OpenAPI עם review אנושי.
- [ ] בדיקות אינטגרציה בסיוע AI וקוד clients ב־PHP/JS/Python.
- [ ] Docker, CI/CD, observability ופריסה מאובטחת.
