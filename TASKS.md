# תוכנית ומשימות — API Studio AI

## מצב נוכחי

- מסלול נוכחי: **Sprint מואץ — 9.11 עד 25.11.2026**.
- יעד פעיל: **להשלים Secure Client Document Hub ברמת portfolio ולהתכונן
  לראיונות Senior Backend / Applied AI**.
- מיצוב קריירה ראשי: **Senior Backend Engineer — AI Systems**.
- מיצוב משני: **Applied AI / Forward Deployed Engineer**.
- פרויקט גמר נבחר: **Secure Client Document Hub** — עובד יוצר בקשת
  מסמכים וקישור העלאה מאובטח המשויך מראש ללקוח ולתיק. הקבצים נשמרים
  בארכיון הלקוח עם metadata, review ו־audit. קליטה ישירה מ־email
  ומ־WhatsApp ויכולות AI יתווספו רק לאחר שה־MVP המאובטח עובד. הפיתוח
  מתחיל במידע סינתטי בלבד.
- Agents SDK, state, approvals ו־sessions הושלמו; LangGraph אינו נדרש כעת.

## חיזוק Python לפני המשך שבוע 2

- [x] יום 1: פונקציות, dictionaries, loops ו־`get()`.
- [x] יום 2: `@dataclass`, בנאי ו־`__post_init__`.
- [x] יום 3: JSON, חריגות וטעינת אובייקטים.
- [x] יום 4: `assert`, ‏`pytest.raises` ו־`parametrize`.
- [x] יום 5: NumPy/Pandas, חזרה ומבחן חוזר של 10 נקודות.
- [x] לבצע מבחן חיזוק Python נוסף ב־2026-11-05; תוצאה: 7.5/10.
- [ ] להשלים חיזוק ממוקד בדיוק תחבירי ולבצע בדיקה קצרה נוספת; יעד: לפחות
  8/10 ללא הכוונה.

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
- [x] להבין tool calling בסיסי: הגדרת tool, בחירת tool וביצוע מבוקר.
- [x] לממש זרימת tool calling מלאה עם allowlist ובדיקות mock ללא רשת.
- [x] לבצע review לבדיקות ה־mock ולהסביר מדוע מדמים שתי תגובות מודל.
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

- [x] לבנות Agent ללא framework מלא: קבלת משימה, החלטה על tool, ביצוע,
  המשך לפי הצורך והחזרת תוצאה סופית.
- [x] להבין את ההבדל בין קריאת LLM יחידה, Tool Calling קבוע ו־Agent loop.
- [x] לממש execution loop עם כמה סבבי tools ומגבלת `max_steps`.
- [x] להוסיף אישור אנושי לפני הפעלת tool רגיש.
- [x] להמשיך את לולאת ה־Agent לאחר ביצוע tool שאושר ולהחזיר תשובה סופית.

## שבוע 4 — Frameworks ו־state

יעדים: OpenAI Agents SDK, יסודות LangGraph, state, memory, workflows,
human-in-the-loop, persistence ודיבוג Agents.

- [x] לשפר את ה־Agent בעזרת framework מתאים ולהסביר מתי framework מועיל.
- [x] להוסיף גרסת OpenAI Agents SDK מקבילה עם `Agent`, ‏`Runner` ו־
  `@function_tool`, בלי להחליף את המימוש הידני.
- [x] להוסיף context והרשאות, human approval ו־state לגרסת ה־SDK.
- [x] להוסיף `SQLiteSession` עם `conversation_id` וגבול של 20 פריטים.
- [x] ללמוד persistence, sessions ו־tracing, ולהשוות בקצרה ל־LangGraph.
- [x] להתחיל תרגול System Design: queues, idempotency, circuit breaker
  ו־transactional outbox.
- [x] להוסיף dataset ו־offline scorer בסיסיים ל־Agent evals ללא מודל חי.
- [x] להתחיל מחקר שוק עבודה, gap analysis, הכנה לראיונות ו־system design.
- [x] לבחור מיצוב קריירה ראשי ומשני בהתאם לניסיון ולדרישות השוק.
- [x] לבחור כיוון לפרויקט הגמר ולהגדיר MVP וגבולות פרטיות ראשוניים.
- [x] להתחיל לחזק את תיק העבודות באמצעות חוזה domain ובדיקות ראשונות
  ל־Secure Client Document Hub; חיפוש עבודה פעיל רק באישור מפורש.

## Sprint מואץ — סיום עד 25.11.2026

המטרה היא לשמור על אותם יעדי הליבה של שבועות 5–8, אך לבצע אותם לפי
תוצרים מדידים. עומק נוסף, Multi-Agent וקליטת WhatsApp ישירה אינם חוסמים
את הסיום.

### 9–12.11 — ליבת Secure Client Document Hub

- [ ] להשלים activation endpoint עם tenant scope, קישור ציבורי מאובטח,
  response model ומיפוי 404/409.
- [ ] להשלים זרימת upload בסיסית עם token hash, expiration, file metadata
  וסטטוס, באמצעות מידע סינתטי בלבד.
- [ ] להריץ migration ובדיקת integration מול PostgreSQL מקומי.
- [ ] לשמור על בדיקות regression ולעבור חיזוק Python קצר דרך הקוד האמיתי.

### 13–15.11 — RAG, MCP ואינטגרציות

- [ ] לבנות vertical slice קטן: עיבוד מסמך סינתטי, retrieval והחזרת
  תשובה עם מקור.
- [ ] לחבר את ה־Agent ל־retrieval ול־API tool עם authentication והרשאות.
- [ ] להבין MCP ולבצע integration קטן אחד; אין צורך לבנות vector platform
  מלאה אם retrieval פשוט מספיק ל־MVP.

### 16–18.11 — System Design, reliability ו־AI evals

- [ ] לתכנן queue ו־workers לעיבוד מסמכים, כולל transactional outbox.
- [ ] לממש idempotency, retries ו־circuit breaker עבור תלות חיצונית אחת.
- [ ] להגדיר evaluation מדיד עם dataset מייצג, איכות, latency, עלות
  וקריטריוני הצלחה.
- [ ] אופציונלי בלבד: Multi-Agent, ורק אם הוא נותן ערך מדיד לעומת Agent
  יחיד.

### 19–21.11 — Production Engineering

- [ ] לארוז את האפליקציה ב־Docker עם configuration ו־secrets מאובטחים.
- [ ] לבנות GitHub Actions עבור tests ו־build, ולהוסיף deployment אם
  סביבת הענן מוכנה.
- [ ] להוסיף structured logging, health checks ומדדי monitoring בסיסיים.
- [ ] לבצע production hardening: הרשאות, rate limits, timeouts, טיפול
  בכשלים ותיעוד rollback/recovery.

### 22–25.11 — סיום פרויקט והכנה לקריירה

- [ ] להשלים Agent מקצה לקצה עם tools, structured output, human approval
  ו־error recovery.
- [ ] לבצע load testing, לזהות צווארי בקבוק ולתעד מגבלות קיבולת.
- [ ] להכין README, תיעוד ארכיטקטורה, תרשים זרימה, החלטות ו־trade-offs
  להצגה בתיק העבודות.
- [ ] להכין demo קצר ותרחישי הצלחה וכשל שניתנים להצגה בראיון.
- [ ] לבצע הכנה ממוקדת לראיונות Senior Backend / Applied AI: System
  Design, Python, Agents, evals ומערכות production.

## אבני דרך מוצר עתידיות — אינן המשימה הנוכחית

- [ ] מנוע HTTP דינמי מאובטח עם מתודות, URL, headers/auth, query, JSON
  ותשובת status/headers/body/time, לאחר הגנות SSRF והרשאות.
- [ ] PostgreSQL, משתמשים, פרויקטים, collections והיסטוריה עם בידוד גישה.
- [ ] ממשק React ו־TypeScript.
- [ ] שיתוף והרשאות.
- [ ] קליטת PDF/OpenAPI עם review אנושי.
- [ ] בדיקות אינטגרציה בסיוע AI וקוד clients ב־PHP/JS/Python.
- [ ] Docker, CI/CD, observability ופריסה מאובטחת.
