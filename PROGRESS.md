# התקדמות מאומתת — API Studio AI

תאריך עדכון אחרון: 2026-11-17.

## מצב הלמידה

- הותחל בלוק Production Engineering עם Docker. המשתמש הסביר ש־API,
  MCP ו־migration שייכים לאותה אפליקציה צריכים להשתמש באותו image; הובהר
  שכך בונים ובודקים artifact אחד ומונעים version drift. נוספו multi-stage
  `Dockerfile`, ־`.dockerignore` ו־Compose עם PostgreSQL, ־migration job חד־פעמי, API
  ו־MCP. ה־containers של האפליקציה מוגדרים non-root, עם filesystem לקריאה בלבד,
  ללא Linux capabilities ועם secrets מ־environment. `docker compose config --quiet`
  עבר, בדיקות configuration ממוקדות עברו **7 passed in 1.24s**, והסוויטה
  המלאה עברה **242 passed, 1 skipped in 8.60s**. בניית image בפועל
  טרם אומתה: Docker Desktop מותקן אך ה־Linux engine אינו פועל, וניסיון
  הפעלה ברקע נסגר מייד. משימת Docker לא סומנה כהושלמה.
- לאחר הפעלת Docker Desktop הושלם אימות Docker בפועל. ה־image
  `api-studio-ai:validation` נבנה בהצלחה, ו־Compose הפעיל PostgreSQL,
  migration, API ו־MCP. פורט 8000 היה תפוס על־ידי container לא קשור,
  ולכן נוספה הגדרת `API_HOST_PORT` וה־smoke test רץ על 8002 בלי לעצור
  מערכת אחרת. FastAPI החזיר את תשובת ה־root הצפויה, MCP החזיר
  **401** ללא token, ו־PostgreSQL דיווח Alembic revision `20261116_0005`.
  ה־API container רץ כ־UID `999` וניסיון כתיבה ל־root filesystem נדחה כ־`read-only`.
  משימת Docker סומנה כהושלמה. ה־API ו־MCP containers נשארו פועלים
  מקומית בסיום האימות.
- הותחל GitHub Actions CI. נוסף workflow שמופעל ב־Pull Request,
  ב־push ל־`main` ובהפעלה ידנית. job ראשון מתקין Python 3.12 ואת
  `requirements-dev.txt` ומריץ Pytest; job שני תלוי בהצלחתו ובונה את
  Docker image. נוספו הרשאות read-only, ביטול ריצות ישנות ו־timeouts.
  פקודת הבדיקות אומתה מקומית: **242 passed, 1 skipped in 20.28s**,
  ו־`docker build --tag api-studio-ai:ci .` הסתיים בהצלחה. לאחר push
  ל־`main`, ריצת GitHub Actions מספר `44066346095` הסתיימה בהצלחה:
  גם `Python tests` וגם `Docker build` עברו. משימת GitHub Actions
  סומנה כהושלמה; deployment נשאר מחוץ להיקף עד לבחירת סביבת ענן.
- הושלמו health checks נפרדים: `GET /health/live` בודק רק שה־FastAPI
  process חי, ו־`GET /health/ready` מריץ `SELECT 1` מול PostgreSQL
  ומחזיר `503` גנרי ללא דליפת פרטי שגיאה כאשר ה־DB אינו זמין. Docker
  עודכן להשתמש ב־liveness. המשתמש זיהה תחילה `400`, תיקן את ההבנה
  ל־`503 Service Unavailable`, וכתב את מבנה ה־`try/except` של readiness.
  אימות ממוקד: **21 passed in 10.78s**; אימות מלא:
  **245 passed, 1 skipped in 19.10s**; `docker compose config --quiet` עבר.
- נוסף structured HTTP logging בפורמט JSON באמצעות Python logging, ללא
  dependency חדש. כל בקשה מקבלת `request_id` אקראי שמוחזר ב־`X-Request-ID`;
  הלוג כולל method, path ללא query string, status ו־duration. אין רישום של
  body, headers, cookies, query parameters או תוכן מסמכים. המשתמש הסביר
  נכון שיש לשמור רק metadata ו־reference בטוחים ולא לחשוף את כל הבקשה.
  נוספה הגדרת `LOG_LEVEL`, ונבדק מפורשות ש־token ב־query וב־Authorization
  אינו מופיע בלוג. אימות ממוקד: **7 passed in 10.87s**; אימות מלא:
  **247 passed, 1 skipped in 18.31s**.
- נוסף endpoint של Prometheus ב־`GET /metrics/` עם counter לבקשות ו־histogram
  לזמן תגובה. ה־labels מוגבלים ל־method, route template ו־status class;
  אין שימוש ב־request/user/customer/document IDs. המשתמש הבין ש־metrics
  מזהים בעיה מצטברת, logs מתארים אירוע ספציפי ו־traces עוקבים אחר מסלול
  בקשה, וכן שהבעיה ב־IDs כ־labels היא high cardinality. בדיקה ייעודית
  מוכיחה ש־ID דינמי אינו מופיע ב־metrics. אימות ממוקד:
  **7 passed in 9.77s**; אימות מלא: **249 passed, 1 skipped in 23.54s**;
  image בשם `api-studio-ai:metrics-validation` נבנה בהצלחה עם dependency
  `prometheus-client==0.26.0`.
- נוספו Prometheus configuration ו־alert rules: target שאינו ניתן ל־scrape
  במשך 2 דקות, שיעור 5xx מעל 5% במשך 5 דקות, ו־p95 latency מעל 2 שניות
  במשך 10 דקות. המשתמש בחר נכון בתנאי מתמשך במקום alert על שגיאה יחידה,
  כדי להבחין בין אירוע נקודתי לבעיה נמשכת. נוסף Compose profile אופציונלי
  ל־Prometheus 3.16.0 על localhost בלבד. `promtool` אימת configuration אחד
  ושלושה rules, ו־`docker compose --profile monitoring config --quiet` עבר.
  Notifications אינם מוגדרים מקומית; בפריסה אמיתית יחובר Alertmanager או
  שירות monitoring של ספק הענן. משימת logging/health/monitoring סומנה כהושלמה.
- הותחל בלוק reliability של queue, workers ו־transactional outbox. המשתמש
  זיהה שבהפעלה חוזרת ה־worker עלול לעבד את אותו job פעם נוספת,
  ושעליו לזהות שהעיבוד כבר הושלם. הובהר שזהו עקרון idempotency
  ושהוא מיושם בפרויקט באמצעות החלפה אטומית של chunks.
- המשתמש הסביר נכון ש־idempotency key דטרמיני מאפשר לזהות retry
  של אותה פעולה, ושנעילת רשומה מונעת משני workers לקבל את אותו
  job. הוא זיהה ש־`SKIP LOCKED` מאפשר ל־workers אחרים לעבוד על jobs
  אחרים במקום להמתין. נוספו migration ומודל `outbox_jobs`, אישור
  אטומי עם enqueue, ו־`claim_next_job()` עם `FOR UPDATE SKIP LOCKED`.
  אימות ממוקד: **6 passed in 2.32s**.
- המשתמש חישב נכון backoff מעריכי של 4 דקות בניסיון השלישי וזיהה
  ש־`locked_at` מאפשר לזהות job שנתקע. נוסף recovery שמחזיר job ל־`pending`
  עם `available_at` עתידי, או מעביר ל־`failed` אחר חמישה ניסיונות.
  אימות ממוקד: **12 passed in 2.41s**. בנוסף, המשתמש זיהה את ה־trade-off
  בין התקדמות חלקית לעקביות, והסביר שאין להחזיק transaction ונעילות
  בזמן I/O ארוך ל־S3; רק שמירת ה־chunks וסיום ה־job יכנסו ל־transaction
  קצרה אחת.
- הושלם תכנון ומימוש ליבת queue/worker מבוססת PostgreSQL outbox:
  אישור מסמך ויצירת job ב־transaction אחת, key דטרמיני וייחודי,
  claim עם `FOR UPDATE SKIP LOCKED`, ־lease עם `locked_at`, ־exponential backoff,
  מספר ניסיונות מרבי, recovery של jobs תקועים ומצב `failed`. שמירת
  chunks נגזרים וסימון job כ־`completed` מתבצעים ב־transaction קצרה
  אחת, בעוד S3 ועיבוד ארוך נשארים מחוץ ל־transaction. אימות ממוקד:
  **19 passed in 3.69s**; אימות מלא: **229 passed, 1 skipped in 19.24s**.
- הושלם Circuit Breaker אסינכרוני סביב S3 עם המצבים `closed`,
  `open` ו־`half_open`, בקשת probe אחת וכשל מהיר כשהמעגל פתוח. Timeouts,
  שגיאות connection ו־5xx נספרות כשלים זמניים; ־401/403 פותחות מייד
  את המעגל; ושגיאות קלט אינן נספרות ככשל S3. המשתמש הסביר נכון
  ש־credentials שגויים לא ישתנו בעקבות retry ולכן אין טעם להמשיך לשלוח
  בקשות. ה־threshold וזמן ה־recovery ניתנים להגדרה. אימות ממוקד:
  **12 passed in 1.02s**; אימות מלא: **234 passed, 1 skipped in 12.52s**.
- הותחל RAG evaluation מדיד. המשתמש בנה eval case לשאלת תקופת
  ביטול והבין שתשובה נכונה עם source שגוי צריכה להיכשל, משום שהיא
  עלולה להיות ניחוש או מידע לא מורשה. הוא אישר שבמקרה של tenant leak
  אסור להציג את התשובה וה־eval נכשל כולו. נוספו dataset סינתטי התחלתי,
  scorer לאיכות, sources, latency, cost ו־tenant isolation, ודוח מצרפי.
  אימות ראשוני: **9 passed in 0.17s**. יעדי ה־MVP הזמניים הם 90%
  pass rate, ־100% source accuracy, ־p95 של עד 2 שניות, עלות ממוצעת של עד
  $0.01 ואפס דליפות; הם יכוילו לאחר baseline מייצג.
- הושלמה הגדרת RAG evaluation עם 20 מקרים סינתטיים בשש קטגוריות:
  factual, no-answer, multi-source, ambiguous, prompt injection ו־tenant isolation.
  ה־scorer בודק required ו־forbidden terms, התאמת sources, ־latency, עלות
  ודליפות; הדוח מציג pass rate כללי ולפי קטגוריה, source/safety
  accuracy, ־p95 latency ועלות ממוצעת. המשתמש הבין ששאלת no-answer
  בודקת abstention ושתשובה ללא מקור צריכה להיכשל. אימות ממוקד:
  **22 passed in 1.54s**; אימות מלא: **242 passed, 1 skipped in 10.01s**.
  טרם הורץ baseline חי עם model/API ולכן לא נטענה טענה על איכות המודל
  בפועל; התשתית וה־gates מוכנים להרצה כשיהיה corpus סינתטי זרוע
  ותקציב model מאושר.
- הותחל חיבור MCP קטן ומאובטח. המשתמש הסביר נכון שהזהות
  ב־JWT צריכה להיבדק מול ה־DB בכל בקשה, כדי לאפשר ביטול
  הרשאות מיידי ולמנוע הסתמכות על `tenant_id` או role שהלקוח
  שולח. הוחלט שכלי MCP לא יחשוף `tenant_id` כפרמטר.
- הושלם MCP resource server קטן עם `MCPServer` ו־Streamable HTTP. הוא
  מאמת את ה־JWT הקיים, טוען משתמש פעיל מה־DB, גוזר משם tenant
  ו־role, וחושף רק `search_documents(query, limit)`. ה־tool משתמש
  באותו שירות retrieval של ה־Agent ומחפש רק approved documents של
  ה־tenant המאומת. המשתמש כתב חוזה tool עם `query`, הבין ש־`ctx`
  מוזרק ואינו חשוף למודל, והסביר למה בודקים הרשאות מול ה־DB
  בכל בקשה. אימות ממוקד: **25 passed in 8.60s**; אימות מלא:
  **215 passed, 1 skipped in 14.41s**. לא בוצעה קריאת model או רשת חיה.
- מסלול נוכחי: **Sprint מואץ — 9.11 עד 25.11.2026**. יעדי שבועות 5–8
  נשמרו אך אורגנו מחדש לפי תוצרים: MVP מאובטח, RAG/MCP קטן, reliability
  ו־evals, production engineering, תיעוד והכנה לראיונות. Multi-Agent
  וקליטת WhatsApp ישירה אינם חוסמים את הדדליין.
- ב־2026-11-08 נבחר כיוון לפרויקט הגמר: **Secure Client Document Hub**.
  המערכת תציג פרופיל לקוח עם כל ההודעות והמסמכים שהתקבלו מערוצי web,
  email ו־WhatsApp, תוך שמירת שיוך אופציונלי לתיק משפטי. הרשאה ללקוח
  מעניקה ב־MVP גישה לכל התיקים והמסמכים שלו; לא יתווסף ACL נפרד לכל תיק.
  גבול tenant בין משרדים יישמר במודל הנתונים, והפיתוח יתחיל רק עם מידע
  סינתטי וללא מסמכי לקוחות אמיתיים.
- ה־MVP צומצם לאחר threat modeling: עובד יבחר לקוח ותיק, יגדיר מסמכים
  נדרשים וייצר קישור העלאה מאובטח המשויך מראש לישויות אלו. הלקוח יעלה
  דרך הקישור והמערכת תשייך את הקבצים ללא ניחוש identity מתוך טופס.
  WhatsApp ישמש בתחילה רק לשליחה ידנית של הקישור; חיבור API ישיר יגיע
  מאוחר יותר. קלט טלפון לא מאומת לא ישייך מידע אוטומטית ללקוח קיים.
- נוסף חוזה domain ראשון ב־`schemas/documents.py`: מודל Pydantic
  `UploadRequest` עם `client_id`, תיק אופציונלי, lifecycle מוגבל,
  expiration ומגבלת 1–20 קבצים. המשתמש הרכיב את השדות לאחר חיזוק של
  `Literal`, union type ו־`Field`; עדיין נדרשה הכוונה בדיוק תחבירי
  ובהזחות. נוספו ארבע בדיקות validation. אימות ממוקד: **4 passed in
  0.52s**. הסוויטה המלאה נתקעה בתוך sandbox ביצירת socket פנימי של
  asyncio ב־Windows; מחוץ ל־sandbox עברה: **72 passed in 2.06s**. לא
  בוצעה קריאת רשת או קריאת OpenAI חיה.
- נוסף lifecycle מפורש לבקשות העלאה ב־`services/upload_requests.py`.
  המשתמש הגדיר את מפת המעברים, הבחין בין set ריק ל־dict ריק, ובחר נכון
  ש־retry של אותו status יהיה no-op idempotent ולא שגיאה. המעברים
  החוקיים מחזירים שנדרשת כתיבה, retry זהה מחזיר שאין שינוי, ומעבר אסור
  מעלה exception ייעודי. אימות ממוקד: **14 passed in 0.15s**. אימות מלא
  מחוץ ל־sandbox: **82 passed in 2.28s**. לא בוצעו קריאות רשת.
- נוסף שירות token מאובטח לקישורי העלאה באמצעות `secrets.token_urlsafe`,
  שמירת SHA-256 hash בלבד והשוואה עם `hmac.compare_digest`. המשתמש בחר
  נכון token אקראי במקום מזהי DB חשופים כדי למנוע enumeration וחשיפת
  פרטי domain. אימות ממוקד: **17 passed in 0.21s**. אימות מלא מחוץ
  ל־sandbox: **85 passed in 3.39s**. לא בוצעו קריאות רשת.
- הותקנה תשתית persistence לקראת PostgreSQL: ‏`SQLAlchemy 2.1.8`,
  ‏`Alembic 1.20.1`, ‏`asyncpg 0.32.0` ו־`aiosqlite 0.22.1` לבדיקות.
  הובהר ההבדל בין Pydantic validation, SQLAlchemy ORM ו־Alembic
  migrations, וכן ש־`token_hash` הוא שדה DB פרטי ואינו נחשף ב־API.
  ‏`pip check` החזיר `No broken requirements found`; אימות מלא מחוץ
  ל־sandbox: **85 passed in 1.95s**.
- נוסף בסיס SQLAlchemy אסינכרוני עם `DeclarativeBase`, יצירת engine
  ו־`async_sessionmaker` שמפיק session נפרד לכל request/task. המשתמש
  בחר integer primary keys והבין שה־session מנהל transaction ומעקב
  שינויים בעוד שה־engine וה־pool משותפים. נוספו מודלים ראשונים עבור
  tenants, clients, matters ו־upload requests. composite foreign keys
  אוכפים שתיק ובקשת העלאה שייכים לאותו tenant ולאותו client. בדיקות DB
  אסינכרוניות עם SQLite בזיכרון אימתו שמירה חוקית ודחיית matter של לקוח
  אחר. אימות ממוקד: **2 passed in 0.53s**; אימות מלא מחוץ ל־sandbox:
  **87 passed in 2.46s**.
- נוספה סביבת Alembic אסינכרונית ו־migration ראשונית שיוצרת לפי סדר
  התלויות tenants, clients, matters ו־upload requests, ומוחקת אותן בסדר
  ההפוך. `DATABASE_URL` נדרש בזמן migration ואינו נשמר בקוד. בדיקת
  migration יצרה DB זמני, הריצה `upgrade head`, אימתה את הטבלאות והריצה
  `downgrade base`. אימות ממוקד: **1 passed in 0.70s**; אימות מלא מחוץ
  ל־sandbox: **88 passed in 4.17s**.
- הוחלט ש־token נוצר רק במעבר `draft -> active`. בהתאם, `token_hash`
  הפך nullable ב־draft ונוסף DB check constraint שמחייב token במצבי
  `active`, ‏`completed` ו־`expired`, מאפשר revoke לפני או אחרי activation,
  ומונע draft עם token. מאחר שה־migration טרם נפרסה או נכנסה ל־commit,
  עודכנה ה־migration הראשונית במקום ליצור revision נוסף. אימות DB
  ו־migration ממוקד: **4 passed in 0.59s**; אימות מלא מחוץ ל־sandbox:
  **89 passed in 2.60s**.
- נוסף `activate_upload_request()` שמייצר raw token, שומר hash, מעביר
  ל־`active` ומבצע commit יחיד; שגיאה גורמת rollback. המשתמש זיהה לאחר
  תיקון שה־status וה־token תלויים זה בזה ולכן חייבים atomic transaction.
  activation של status שאינו draft נדחה, וה־raw token אינו נשמר. אימות
  ממוקד: **12 passed in 0.41s**; אימות מלא מחוץ ל־sandbox: **91 passed
  in 2.53s**.
- activation הוקשח ל־atomic conditional update עם תנאי `status = draft`
  ו־tenant scope, כך שרק request מתחרה אחד יכול ליצור token תקף. ניסיון
  activation נוסף אינו מחליף את ה־hash הראשון ומעלה conflict. במהלך
  הבדיקות נמצא ש־rollback מסמן ORM objects כ־expired; הבדיקה תוקנה לבצע
  `session.refresh()` מפורש במקום להפעיל implicit async I/O. אימות ממוקד:
  **13 passed in 0.45s**; אימות מלא מחוץ ל־sandbox: **92 passed in
  2.89s**.
- כאשר conditional activation מעדכן אפס שורות, השירות מבצע lookup נוסף
  בתוך אותו tenant בלבד: רשומה שאינה קיימת או שייכת ל־tenant אחר מעלה
  `UploadRequestNotFound` המיועד ל־404, ורשומה קיימת שאינה draft מעלה
  `UploadRequestActivationConflict` המיועד ל־409. המשתמש מיפה נכון את
  שני המצבים. אימות ממוקד: **14 passed in 0.48s**; אימות מלא מחוץ
  ל־sandbox: **93 passed in 3.08s**.
- ב־2026-11-08 המשתמש בחר במיצוב ראשי **Senior Backend Engineer — AI
  Systems** ובמיצוב משני **Applied AI / Forward Deployed Engineer**.
  המשך התוכנית יתעדף Python עצמאי, system design, distributed systems,
  reliability ו־production delivery, ובמקביל יבנה יכולות RAG, evals
  ואינטגרציות הנדרשות למסלול המשני.
- ב־2026-11-08 החל מחקר שוק עדכני לתפקידי Forward Deployed Engineer,
  Applied AI Engineer ו־Senior Backend for AI בישראל. מודעות פעילות חזרו
  על Python חזק, פתרון בעיות עסקיות עמומות מקצה לקצה, RAG/agents/tool
  calling, evals מדידים, distributed systems, cloud, CI/CD, observability
  והפעלת מערכות production. החוזקות הקיימות הן ניסיון backend ו־APIs,
  ארכיטקטורה, tool calling, approvals ובדיקות; הפערים העיקריים הם עצמאות
  תחבירית ב־Python, RAG/MCP, פריסת cloud ו־production observability,
  evaluation חי ותיק עבודות מקצה לקצה.
- ב־2026-11-08 הושלם תרגול ראיון System Design נוסף. המשתמש בחר `202`
  עבור approval ועבודה ארוכה, DB משותף ל־state עמיד, `approval_id`
  כ־idempotency key, מעבר אטומי ל־`executing` ובדיקת המערכת החיצונית לפני
  retry של רשומה תקועה. הוא הסביר את מצבי circuit breaker; חודד שהמצבים
  מייצגים את מדיניות ה־breaker ולא ודאות שמצב השירות החיצוני תקין או לא.
- ב־2026-11-08 בוצע בלוק חיזוק ממוקד בתחביר Python: מילון מקונן לבקשת
  tool, הפעלת handler אסינכרוני מתוך allowlist ובדיקת pytest פרמטרית.
  המשתמש השלים את שלושת המבנים, אך נדרשה הכוונה בשמות מפתחות במילון,
  בהבחנה בין שם tool ל־handler ובהצמדת הבדיקה למחלקה הנכונה. לכן יעד
  8/10 ללא הכוונה נשאר פתוח ואינו חוסם את המשך שבוע 4.
- ב־2026-11-05 הושלם מבחן חיזוק Python נוסף בתוצאה **7.5/10**. המשתמש
  פתר נכון ספירת מילון, `dataclass` וולידציה, טעינת JSON, Pydantic,
  Pandas, NumPy, async tool execution ומבנה eval לאחר הכוונה. נקודת
  החיזוק המרכזית שנותרה היא דיוק תחבירי עצמאי: הזחות, פסיקים, `:` בתוך
  מילון, איות שמות API, `await`, סוגריים מרובעים בסינון NumPy והבחנה בין
  מחרוזת לשם משתנה. יעד 8/10 ללא הכוונה עדיין פתוח.
- ב־2026-11-02 המשתמש אישר מעבר לשבוע 4. יעד פעיל: להבין מה OpenAI
  Agents SDK מנהל עבורנו לעומת הלולאה הידנית, ומה חייב להישאר באחריות
  האפליקציה. טרם נוסף framework לקוד.
- יעד שהושלם: **גרסת OpenAI Agents SDK בסיסית במקביל למימוש הידני**.
  המשתמש זיהה ש־`Runner` מחליף בעיקר את execution loop, ש־`@function_tool`
  מחבר schema ו־handler אך אינו מחליף הרשאות, וש־`user_id` והרשאות מגיעים
  מה־server context בעוד arguments עסקיים יכולים להגיע מהמודל. הוא הבדיל
  גם בין `RunResult` לבין `final_output` ובין פלט טקסטואלי לפלט Pydantic.
- הותקן וננעל `openai-agents==0.24.0`. נוסף `services/sdk_agent.py` עם
  `Agent`, ‏`Runner`, כלי balance שנוצר מחתימת Python ומגבלת חמישה turns.
  המימוש הידני נשמר ללא החלפה לצורך השוואה ו־fallback.
- אימות ממוקד ב־2026-11-03: **2 passed in 6.97s**. אימות מלא:
  **60 passed in 9.27s**. ‏`pip check` החזיר `No broken requirements
  found.` הבדיקות השתמשו ב־Runner מדומה; לא בוצעה קריאת OpenAI חיה,
  לא נדרש API key ולא נצרכה עלות.
- יעד פעיל הבא: context והרשאות, human approval ו־state בגרסת ה־SDK.
- יעד שהושלם: **Context, הרשאות ו־human approval ב־Agents SDK**.
  המשתמש הבחין ש־`needs_approval=True` דורש אישור אך אינו מעניק הרשאה,
  כתב חתימת tool רגישה, זיהה `result.interruptions`, יצר `RunState`
  באמצעות `to_state()`, והבין שהאפליקציה יוצרת `approval_id` ושומרת את
  ה־state בצד השרת.
- נוספו `AppContext`, כלי מחיקה דמו עם `needs_approval=True`, אחסון זמני
  של `RunState`, בדיקת בעלות והרשאות לפני `state.approve()`, והמשך Runner
  מאותו state. הרשאות נבדקות מחדש בזמן האישור ולא רק בתחילת ההרצה.
- אימות ממוקד ב־2026-11-03: **6 passed in 7.11s**. אימות מלא:
  **64 passed in 9.07s**. כל בדיקות ה־SDK משתמשות ב־mocks בלבד; לא בוצעה
  קריאת OpenAI חיה ולא נצרכה עלות.
- יעד פעיל הבא: persistence, sessions ו־tracing, ולאחר מכן השוואה קצרה
  ל־LangGraph לפני החלטה אם יש בו צורך בפרויקט.
- יעד שהושלם: **Sessions ו־persistence בסיסי ב־Agents SDK**. המשתמש הבדיל
  בין `RunState` להמשך הרצה שנעצרה לבין `Session` לזיכרון בין הודעות,
  זיהה ש־`conversation_id` הוא מזהה השיחה, והבין שה־Runner מקבל אובייקט
  Session ולא מחרוזת ID.
- נוספה `answer_with_sdk_session()` עם `SQLiteSession`, גבול של 20 items,
  `max_turns=5` וסגירת חיבור ב־`finally`. בדיקה מקומית שמרה פריט ב־SQLite,
  סגרה את החיבור, פתחה Session חדש ואימתה שהמידע נשמר.
- אימות ממוקד ב־2026-11-03: **7 passed in 5.55s**. אימות מלא:
  **65 passed in 6.29s**. לא בוצעה קריאת OpenAI חיה ולא נצרכה עלות.
- יעד פעיל הבא: tracing והשוואה קצרה בין Agents SDK ל־LangGraph.
- יעד שהושלם: **בחירת framework לפי אופי הבעיה**. המשתמש זיהה ש־Agents
  SDK מתאים לבקשות בשפה טבעית שבהן המודל צריך להבין כוונה ולבחור כלים
  ומסלול דינמי. הובהר שמסלול קבוע מתאים קודם כול לקוד רגיל, ו־LangGraph
  מוצדק רק כאשר יש workflow ארוך ומסתעף, state מתמשך, pauses ו־recovery
  מורכב.
- LangGraph לא הותקן, משום שאין לו כרגע ערך מדיד לעומת Agents SDK בפרויקט.
  יעדי framework, state, approvals, sessions ו־tracing של שבוע 4 הושלמו.
- יעד פעיל הבא: System Design ו־gap analysis לשוק העבודה, כחלק מהכנת
  Senior Backend / Applied AI שנדרשת החל משבוע 4.
- יעד שהושלם: **תרגול System Design ראשון למערכת Agent אסינכרונית**.
  המשתמש בחר נכון להחזיר `202/pending` בזמן human approval, לשמור state
  במסד נתונים משותף, להעביר עבודה איטית ל־queue, ולמנוע ביצוע כפול בעזרת
  `approval_id` כ־idempotency key ומעבר status אטומי.
- המשתמש הבין retries עם אותו idempotency key, את מצבי circuit breaker
  (`closed`, `open`, `half-open`), הודעות queue שמכילות identifiers בלבד,
  ואת transactional outbox שמונע אובדן job בין commit לפרסום. משימות
  המימוש של שבוע 6 נשארו פתוחות; זהו תרגול ארכיטקטורה בלבד.
- יעד פעיל הבא: gap analysis לשוק העבודה והכנה לראיונות Senior Backend /
  Applied AI, תוך המשך חיזוק System Design.
- יעד שהושלם: **תשתית Agent eval מקומית**. המשתמש הבחין בין unit test
  ללוגיקה דטרמיניסטית לבין AI eval לבחירת tool, arguments והתנהגות מודל,
  והגדיר נכון expected tool, arguments ו־approval עבור פעולת מחיקה.
- נוסף dataset עם ארבעה מקרי בסיס: balance, מחיקה שדורשת אישור, ניסיון
  מחיקה ללא הרשאה ובקשה שחסר בה customer ID. נוסף scorer שמפריד בין
  requested tool לבין executed tool כדי למדוד גם model behavior וגם
  system safety.
- אימות ממוקד ב־2026-11-03: **3 passed in 0.40s**. אימות מלא:
  **68 passed in 6.44s**. לא הורץ מודל חי; זוהי תשתית offline בלבד ולכן
  יעד ה־evaluation המדיד המלא של שבוע 6 נשאר פתוח.
- יעד שהושלם: **Agent execution loop בסיסי**. המשתמש הרכיב לולאה ששומרת
  את היסטוריית הקלט והפלט, מאתרת את כל קריאות הכלים, מפעילה handlers
  מתוך allowlist, מחזירה כל תוצאה באמצעות `call_id`, וממשיכה עד לקבלת
  טקסט סופי. הוא הוסיף `max_steps` ועצירה לפני הפעלת כלים נוספים בצעד
  האחרון.
- המימוש נשמר ב־`services/agent.py` ונוספו שלוש בדיקות mock: תשובה ישירה,
  שני סבבי tools רצופים, ועצירה בגבול הצעדים. אימות ממוקד ב־2026-11-01:
  **3 passed in 1.41s**. אימות מלא: **48 passed in 1.23s**. לא בוצעו
  קריאות רשת, לא נעשה שימוש ב־API key ולא נצרכה עלות.
- יעד שהושלם: **אישור אנושי לפני הפעלת tool רגיש**. המשתמש הגדיר את
  ההבדל בין הרשאה לאישור, זיהה צורך ב־`user_id`, ‏`call_id`, ‏arguments
  וסטטוסים, כתב מודל Pydantic, בדיקת membership ב־`set`, שמירה במילון
  זמני, בדיקת בעלות ואישור רק ממצב `pending`.
- נוסף `ToolApproval`, אחסון זמני בזיכרון, יצירת UUID, עצירת ה־Agent לפני
  כלי רגיש, אישור לפי בעלות וביצוע נפרד רק ממצב `approved`. כלי המחיקה
  הוא דמו דטרמיניסטי ואינו מוחק נתונים אמיתיים. כשל בביצוע מעביר את
  הבקשה ל־`failed`; הצלחה מעבירה ל־`completed`.
- אימות ממוקד ב־2026-11-01: **12 passed in 0.97s**. לאחר הוספת בדיקת
  failure recovery, אימות מלא: **55 passed in 1.08s**. הבדיקות השתמשו
  ב־mocks בלבד; לא בוצעה קריאת
  OpenAI חיה, לא נדרש API key ולא נצרכה עלות.
- יעד פעיל הבא: **המשך Agent לאחר ביצוע tool שאושר**, באמצעות החזרת
  `function_call_output` המתאים למודל וקבלת תשובה סופית.
- יעד שהושלם: **Resume של Agent לאחר אישור אנושי**. המשתמש זיהה שיש
  לשמור את כל `input_items`, להשתמש ב־`approval_id` כמפתח ייחודי,
  לאמת בעלות באמצעות `user_id`, להחזיר את תוצאת הכלי עם `call_id`,
  ולהוסיף dictionary יחיד באמצעות `append()` ולא `extend()`.
- נוסף אחסון זמני של Agent state, שליפה חד־פעמית עם `pop()`, פונקציית
  `resume_agent()` ולולאה פנימית משותפת ל־start ול־resume. משתמש זר נחסם,
  כלי שלא אושר אינו מתבצע, ולאחר הצלחה `function_call_output` נשלח למודל
  לצורך תשובה סופית.
- אימות ממוקד ב־2026-11-01: **13 passed in 1.57s**. אימות מלא:
  **58 passed in 2.73s**. כל הבדיקות מקומיות ומשתמשות ב־mocks; לא בוצעה
  קריאת OpenAI חיה ולא נצרכה עלות.
- יעדי הליבה של שבוע 3 הושלמו. מעבר לשבוע 4 ממתין לאישור המשתמש. האחסון
  הנוכחי נשאר in-memory לצורכי למידה ואינו מיועד ל־production או לכמה
  workers.
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
- יעד שהושלם: **יסודות tool calling**. המשתמש הגדיר את חלקי ה־tool schema,
  הבין שהמודל מחזיר `function_call` אך אינו מפעיל קוד, פענח arguments,
  בחר כלי מתוך allowlist, זיהה כלי לא מוכר באמצעות `None`, והפעיל כלי
  אסינכרוני עם `await` ו־`**arguments`. הוא הסביר נכון ש־`call_id` מקשר
  בין כל בקשת כלי לתוצאה שלה, ושבזרימה הרגילה נדרשת קריאה שנייה למודל
  לאחר `function_call_output` כדי לנסח תשובה סופית.
- יעד פעיל הבא: מימוש זרימת tool calling מלאה עם mock בלבד, ללא API key,
  רשת או עלות.
- יעד שהושלם: **מימוש Tool Calling מלא עם allowlist**. לאחר שהמשתמש
  הרכיב את הזרימה בשלבים, נוסף `services/tool_calling.py` עם הגדרת tool,
  מיפוי מפורש ל־handler, פענוח arguments, הפעלת פונקציה אסינכרונית,
  החזרת `function_call_output` וקריאה שנייה למודל. נוספו מסלולים לתשובה
  ללא tool ולדחיית שם כלי שאינו מורשה.
- נוספו שלוש בדיקות mock ללא API key, רשת או עלות. אימות ממוקד
  ב־2026-10-30: **3 passed in 0.62s**. אימות מלא מחוץ ל־sandbox:
  **45 passed in 1.17s**.
- יעד פעיל הבא: review של בדיקות ה־mock והבנת הדרך שבה fake client מדמה
  שתי תשובות עוקבות של Responses API.
- יעד שהושלם: **review של בדיקות Tool Calling עם mock**. המשתמש הסביר
  ש־`first_response` עשויה להיות תשובה ישירה או בקשה לכלים, ושלאחר
  הפעלת הכלים `final_response` מייצגת את תשובת המודל הבאה. הוא זיהה
  נכון שבמערכת מלאה גם התגובה הבאה עשויה לבקש כלים נוספים, ולכן נדרש
  execution loop ולא תמיד די בשתי קריאות קבועות.
- יעדי שבוע 2 הושלמו ברמת התרגול והבדיקות המקומיות. מעבר לשבוע 3 —
  בניית Agent מאפס — ממתין לאישור המשתמש.
- ב־2026-11-01 המשתמש אישר מעבר לשבוע 3. יעד פעיל: להבין מה הופך
  Tool Calling ל־Agent execution loop, לפני שינוי המימוש הקיים.
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

- המשתמש בחר נכון `get_current_user` עבור endpoint ה־Agent משום שנדרשים
  user ID, tenant ID ו־role לקביעת הרשאות. הוא תיקן constraints של
  מחרוזות מ־`ge/le` ל־`min_length/max_length` והגדיר request/response
  models עם `Field`. נוסף endpoint מאומת
  `POST /api/v1/ai/agent/documents/answer`, שמייצר server context מהמשתמש
  המאומת ומעביר allowlist לפי role. גם `admin` וגם `staff` מקבלים כרגע
  רק search read-only; role לא ידוע מקבל set ריק. אימות ממוקד:
  **29 passed in 8.54s**; אימות מלא:
  **210 passed, 1 skipped in 14.03s**. משימת Agent + retrieval +
  authentication סומנה כהושלמה.

- המשתמש כתב נכון חתימת `sdk_search_documents(query, limit)` ללא
  `tenant_id` או DB session שנשלטים בידי המודל. הוא הגדיר
  `DocumentAgentContext` עם user, tenant, session ו־`set[str]` של tools,
  הבין שהשרת יוצר אותו לאחר authentication, ותיקן membership check אל
  `"sdk_search_documents" not in context.context.allowed_tools`. לאחר מכן
  העביר ל־retrieval את ה־session וה־tenant מתוך server context. נוסף
  `sdk_search_documents` read-only tool ו־`document_agent`; ה־tool schema
  חושף למודל רק `query` ו־`limit`, בעוד allowlist, tenant ו־session נשארים
  בצד השרת. הובהר שב־strict Agents SDK schema גם `limit` עם default מופיע
  ב־`required`. אימות ממוקד: **11 passed in 6.36s**; אימות מלא:
  **201 passed, 1 skipped in 19.89s**.

- המשתמש בנה `RagQuestion` עם `Field`, תיקן שגיאות כתיב בתחביר Python
  והגדיר `question` באורך 1–2000 ו־`limit` עם ברירת מחדל 3 ובטווח 1–10.
  נוסף `POST /api/v1/ai/rag/answer` מאומת: tenant מגיע מה־JWT ולא מה־body,
  וה־OpenAPI מציג `RagQuestion` ו־`RagAnswer`. בדיקות ממוקדות:
  **16 passed in 5.39s**. בדיקת vertical slice אמיתית חיברה טקסט סינתטי,
  chunking, שמירה אטומית, retrieval, מודל מדומה ותשובה עם sources:
  **1 passed in 3.27s**. אימות מלא סופי:
  **197 passed, 1 skipped in 13.74s**. משימת ה־RAG vertical slice סומנה
  כהושלמה; אין עדיין PDF extraction, malware worker, embeddings או מודל חי.

- המשתמש הסביר נכון שאין טעם לקרוא למודל כאשר retrieval לא מחזיר context,
  משום שאין evidence והקריאה רק מוסיפה hallucination risk, עלות ו־latency.
  המשתמש גם בחר נכון שהשרת יבנה `RagSource` מה־IDs שכבר נוצרו ב־DB ולא
  יאפשר למודל להמציא metadata; לאחר תיקון הוא מיפה נכון
  `chunk.chunk_id`, ‏`document_submission_id` ו־`position`. נוסף
  `answer_question_with_rag()` עם short-circuit ללא context, הנחיה להתייחס
  ל־document context כמידע לא־מהימן, structured model output ובניית sources
  בצד השרת. כל בדיקות OpenAI משתמשות ב־mock ללא רשת או עלות. אימות ממוקד:
  **17 passed in 3.25s**; אימות מלא:
  **189 passed, 1 skipped in 13.78s**.

- המשתמש הבחין בין class בשם `DocumentChunk` לבין instance בשם `chunk`,
  וזיהה את ארבעת השדות הנדרשים ל־prompt source metadata. לאחר מכן שילב
  `format_chunk_for_prompt(chunk)` בתוך לולאה על tuples מסוג
  `(score, chunk)` וחיבר את התוצאות ל־context אחד. נוספו בדיקות ל־metadata,
  הפרדה בין chunks ומצב ללא תוצאות. אימות ממוקד:
  **8 passed in 1.54s**; אימות מלא:
  **185 passed, 1 skipped in 16.97s**.

- המשתמש הגדיר נכון `RagSource` עם מזהי chunk/submission ו־position,
  ותיקן את `RagAnswer.sources` מ־`Literal` ומ־`list` לא ממוקד אל
  `list[RagSource]`, כך ש־Pydantic מאמת כל source object בנפרד. נוספו
  constraints חיוביים למזהים, position לא שלילי ותשובה לא ריקה. אימות
  ממוקד: **5 passed in 0.11s**; אימות מלא:
  **182 passed, 1 skipped in 4.88s**.

- המשתמש נעזר בתרשים ER מלא כדי להבין את מסלול ה־FKs, ואז חיבר נכון
  `DocumentChunkRow` ל־`DocumentSubmissionRow`, משם ל־
  `DocumentRequirementRow` ול־`UploadRequestRow`. המשתמש זיהה נכון שסינון
  tenant צריך להשתמש ב־`UploadRequestRow.tenant_id` ושב־SQLAlchemy
  משתמשים בשם ה־ORM model ולא בשם הטבלה. נוסף `retrieve_tenant_chunks()`
  שמבצע tenant filter ו־status filter בתוך SQL לפני lexical scoring
  ב־Python. בדיקה עם שני משרדים הוכיחה שגם chunk ממשרד אחר עם ציון גבוה
  יותר אינו נכנס לתוצאות. אימות ממוקד: **6 passed in 0.81s**; אימות מלא:
  **177 passed, 1 skipped in 6.39s**.

- המשתמש בחר נכון `ON DELETE CASCADE` עבור chunks שהם derived data של
  submission, והבין ששם מפורש ל־unique constraint משמש את PostgreSQL,
  migrations והלוגים ואינו עמודה. נוספו `DocumentChunkRow` ו־migration
  `20261112_0004` עם `TEXT`, ‏position לא שלילי, תוכן לא ריק וייחודיות
  `(document_submission_id, position)`. הטבלה נשארה מנורמלת; tenant scope
  ייאכף דרך join ל־upload request לפני ranking. בדיקות model/migration:
  **5 passed in 1.96s**; migration אמיתית ובדיקת PostgreSQL:
  **1 passed in 0.72s**; אימות מלא: **172 passed, 1 skipped in 17.34s**.
  המשתמש למד `enumerate()` ומיפה נכון כל `(position, content)` ל־
  `DocumentChunkRow` עם `document_submission_id` משותף. המשתמש בחר נכון
  בהחלפה אטומית של chunks עבור retry של אותו job. נוסף
  `replace_document_chunks()` שנועל submission מאושר, מוחק ומכניס מחדש
  באותה transaction ומבצע rollback בכשל. אימות ממוקד:
  **4 passed in 1.11s**; אימות מלא: **176 passed, 1 skipped in 11.77s**.

- המשתמש בנה נכון את אלגוריתם חלוקת הטקסט ל־chunks: ‏`split()`, חיתוך
  `words[start:start + max_words]`, חיבור עם `" ".join(...)`, ‏`append`
  בתוך הלולאה ו־`return` לאחריה. הובהר שהקובץ המקורי נשמר ב־S3, בעוד
  chunks נגזרים נשמרים כ־rows ועמודות רגילות ב־PostgreSQL; ‏`pgvector`
  מוסיף יכולת חיפוש סמנטי ואינו מחליף את PostgreSQL. נוספו שירות
  `document_processing.py` ובדיקות ל־word order, whitespace, טקסט ריק
  וגודל chunk לא חוקי. בדיקות processing ו־retrieval:
  **10 passed in 0.13s**; אימות מלא: **168 passed, 1 skipped in 14.39s**.

- התחיל vertical slice של RAG. המשתמש הגדיר נכון `DocumentChunk` כ־
  `@dataclass(frozen=True)` עם `chunk_id`, ‏`tenant_id`,
  `document_submission_id`, ‏`content` ו־`position`. הוחלט להתחיל ב־
  retrieval דטרמיניסטי לפני הוספת embeddings/vector database, כדי לאמת
  תחילה tenant isolation, מקורות וזרימת RAG מקצה לקצה. המשתמש הסביר נכון
  שהסינון לפי tenant חייב לקרות לפני retrieval כדי שמסמכים ממשרד אחר לא
  ייכנסו כלל ל־candidate set, ומימש סינון של `DocumentChunk` באמצעות
  `item.tenant_id == tenant_id` בלי לשנות את הרשימה המקורית. לאחר תרגול
  `any()` ו־generator expression, המשתמש מימש matcher שאוסף query words
  עם `lower().split()` ובודק כל מילה מול תוכן chunk מנורמל. הובהר ההבדל
  בין חיפוש מילים נפרדות, חיפוש phrase מלא ו־substring matching. המשתמש
  החליף `any()` ב־`sum()` ומימש `calculate_chunk_score()` שמחזיר מספר
  שלם לפי מספר מילות השאילתה שמופיעות בתוכן, כבסיס לדירוג תוצאות. לאחר
  תיקון typo ותרגול `continue` ו־`list.append`, המשתמש שילב tenant filter
  עם scoring ושמר כל תוצאה חיובית כ־tuple מסוג `(score, chunk)`. נוספה
  תשתית retrieval דטרמיניסטית ב־`services/retrieval.py`, כולל דירוג יורד,
  `limit` ובדיקות מפורשות שמונעות דליפה בין tenants. אימות ממוקד:
  **5 passed in 0.03s**; אימות מלא: **163 passed, 1 skipped in 11.22s**.

- תרגיל חיזוק Python מתוך מנגנון recovery: המשתמש כתב פונקציה שסורקת
  submissions, מסננת `uploading` שנוצרו לפני `cutoff`, אוספת את המזהים
  ומחזירה `list[int]`. לאחר review תוקנו גישה ל־dict, ‏`and`, שם השדה,
  נקודתיים והחזרת הרשימה. הלוגיקה הסופית נכונה.

- הופעל PostgreSQL 18.6 מקומי ב־Docker על `127.0.0.1:5433`, כדי לא
  להתנגש ב־PostgreSQL אחר שכבר משתמש בפורט 5432. הרצת Alembic אמיתית
  חשפה default לא נייד: SQLite קיבל `1` עבור Boolean, אך PostgreSQL דחה
  אותו. ה־migration והמודל תוקנו להשתמש ב־SQL `true`. כל שלושת ה־
  migrations עלו בהצלחה; בדיקת PostgreSQL המפורשת עברה:
  **1 passed in 1.93s**. לאחר מכן הסוויטה המלאה עברה:
  **158 passed, 1 skipped in 25.05s**; ה־skip הוא בדיקת PostgreSQL
  המפורשת כאשר `TEST_POSTGRES_URL` אינו מוגדר.

- הושלמה זרימת upload ציבורית בסיסית. היא מאמתת upload-session cookie,
  בודקת מחדש request פעיל ולא פג, requirement מתאים ומגבלת קבצים, יוצרת
  reservation אטומית בסטטוס `uploading`, שומרת ב־S3/local storage ואז
  מעבירה ל־`pending_scan`. כשל אחסון נשמר כ־`upload_failed`; כשל finalization
  משאיר state בר־שחזור. בדיקות אינטגרציה אימתו גם את שלושת תנאי link token:
  hash, status ו־expiration. אימות ממוקד: **6 passed in 3.28s**; אימות
  מלא מחוץ לבידוד: **158 passed in 12.82s**. scanner worker עדיין אינו
  ממומש; קבצים ב־`pending_scan` אינם מיועדים להורדה.

- המשתמש בחר להשאיר את link token תקף עד expiration והבין ש־session
  cookie אינו יכול לחיות מעבר להרשאה שיצרה אותו. activation URL שונה
  ל־fragment כדי למנוע שליחת raw token אוטומטית לשרת. נוסף exchange
  endpoint שמקבל את ה־token ב־header ומחזיר cookie קצר־חיים עם
  `HttpOnly`, ‏`Secure` ו־`SameSite=Strict`; access token רגיל אינו תקף
  כ־upload session. אימות ממוקד: **26 passed in 6.71s**; אימות מלא מחוץ
  לבידוד: **152 passed in 18.24s**.

- המשתמש בחר מגבלת 15MB ושאל מדוע ליצור temporary file נוסף. בעקבות
  ה־review הוסר הצורך בהעתקה נוספת: השירות קורא את `UploadFile` הקיים
  ב־chunks, מחשב size ו־SHA-256, מבצע rewind ומעביר את אותו buffer
  לאחסון. נוספו validation לקובץ ריק, חריגה מהמגבלה ושם metadata לא
  חוקי. אימות ממוקד: **8 passed in 1.06s**; אימות מלא מחוץ לבידוד:
  **142 passed in 17.78s**.

- המשתמש בחר ש־`document_requirement_id` יגיע עם הקובץ, תוך אימות שהוא
  שייך ל־upload request שמזוהה על ידי ה־token, ובחר לשמור submission
  history מלא. נוספו טבלאות `document_requirements` ו־
  `document_submissions` ב־migration חדשה, כולל metadata, storage key
  ייחודי, SHA-256, גודל ו־status שמתחיל ב־`pending_scan`. ‏DB constraints
  דוחים קובץ ריק וסטטוס לא חוקי. אימות ממוקד:
  **4 passed in 2.30s**; אימות מלא מחוץ לבידוד:
  **134 passed in 12.37s**.

- המשתמש הבין שה־original filename נשמר ב־DB לצורך תצוגה וחיפוש אך אינו
  שולט בנתיב האחסון, וביקש להוסיף S3. נוספו `FileStorage` abstraction,
  אחסון מקומי אטומי לפיתוח ו־S3 adapter עם server-generated key,
  tenant/request scope, private upload ו־SSE-S3. ‏Boto3 משתמש ב־credential
  provider chain ואינו מקבל credentials מהקוד. כל בדיקות S3 משתמשות
  ב־fake client ללא רשת. אימות ממוקד מחוץ לבידוד:
  **7 passed in 1.20s**; `pip check` תקין; אימות מלא:
  **131 passed in 17.51s**.

- המשתמש בחר ליצור את ה־tenant וה־admin הראשון באמצעות פקודת bootstrap
  מקומית ולא endpoint ציבורי, והסביר שכשל ביצירת admin חייב לבצע rollback
  גם ל־tenant. נוספו service אטומי, CLI עם password prompt מוסתר ותיעוד
  הפעלה ב־README. בדיקה אימתה rollback במקרה של email כפול. אימות ממוקד:
  **2 passed in 3.65s**; אימות מלא מחוץ לבידוד:
  **126 passed in 16.09s**.

- המשתמש בחר נכון ש־authentication dependency תחזיר אובייקט פנימי עם
  `user_id`, ‏`tenant_id` ו־`role`, ולא רק tenant ID. נוסף
  `AuthenticatedUser` קפוא, Bearer extraction, אימות JWT, טעינת user
  עדכני מה־DB ובדיקת `is_active`. ה־activation route מקבל tenant scope
  מהמשתמש המאומת ולא מהלקוח. אימות ממוקד: **7 passed in 4.80s**;
  אימות מלא מחוץ לבידוד: **124 passed in 11.42s**.

- המשתמש בנה את מבנה `LoginRequest` לאחר תיקון constraints ל־`Field`
  ואת `TokenResponse` לאחר תיקון שם השדה ותחביר `Literal`. נוסף
  `POST /api/v1/auth/login` שמחזיר Bearer token, ממפה credentials שגויים
  ל־401 אחיד ומבצע validation לקלט. אימות routes ו־OpenAPI:
  **23 passed in 5.06s**; אימות מלא מחוץ לבידוד:
  **121 passed in 10.82s**.

- המשתמש הסביר נכון ש־email עובר `strip().lower()`, שהשאילתה מחפשת
  משתמש לפי email בלבד, ושכל סיסמה נבדקת מול hash עם salt משלה. נוסף
  שירות login שמבצע dummy Argon2 verification למשתמש שאינו קיים ומחזיר
  אותה חריגה עבור email שגוי, password שגוי או משתמש לא פעיל, כדי לצמצם
  user enumeration. אימות ממוקד: **8 passed in 3.33s**; אימות מלא מחוץ
  לבידוד: **116 passed in 14.11s**.

- המשתמש זיהה ש־JWT `sub` צריך להכיל `str(user_id)` ושחיבור דקות ל־
  `datetime` מחייב `timedelta`. נוספו הגדרות server-only עבור secret,
  issuer, audience ותוקף; יצירת JWT עם `sub/iss/aud/iat/exp`; ואימות
  חתימה, audience, issuer, expiration ו־claims נדרשים. בדיקות דחו token
  שפג תוקפו, secret שגוי ו־token ללא subject. אימות ממוקד:
  **10 passed in 3.78s**; `pip check` תקין; אימות מלא מחוץ לבידוד:
  **112 passed in 13.27s**.

- המשתמש זיהה נכון שב־Argon2 בודקים סיסמה באמצעות `verify` ולא באמצעות
  hash חדש והשוואת `==`, משום שכל hash משתמש ב־salt אקראי. נוספו
  `pwdlib[argon2] 0.3.1`, ‏`PyJWT 2.15.1` ושירות hashing קטן. הבדיקות
  מאמתות שה־plaintext אינו נשמר, סיסמה נכונה מתקבלת, שגויה נדחית ושני
  hashes לאותה סיסמה שונים. אימות ממוקד: **4 passed in 0.79s**;
  `pip check` תקין; אימות מלא: **108 passed in 9.06s**.

- המשתמש בחר authentication לפי email ייחודי גלובלי והסיר `username`
  שאינו מוסיף ערך ל־MVP. הוגדרו roles מינימליים `admin` ו־`staff`, עם
  ברירת מחדל `staff`, ונוספה טבלת `users` ב־migration חדשה משום
  שה־migration הראשונית כבר פורסמה. הסיסמה מיוצגת רק כ־`password_hash`.
  בדיקות אימתו defaults, ייחודיות email גלובלית ו־DB constraint על role.
  אימות ממוקד: **4 passed in 0.60s**; אימות מלא מחוץ לבידוד:
  **104 passed in 2.90s**.

- נוסף activation endpoint מלא עם tenant dependency, DB session לכל
  request, ‏`PUBLIC_BASE_URL`, מיפוי 404/409 ותגובה שאינה חושפת token
  בנפרד. ה־engine וה־pool נוצרים פעם אחת ב־FastAPI lifespan ונסגרים
  בכיבוי; כל request מקבל `AsyncSession` נפרד. עד למימוש JWT אמיתי,
  authentication נכשל בצורה בטוחה עם 401 והבדיקות משתמשות ב־dependency
  override. תוקן גם סדר העדיפויות של Alembic כך ש־URL מפורש קודם למשתנה
  סביבה. אימות ממוקד: **19 passed in 1.64s**; אימות מלא מחוץ לבידוד:
  **101 passed in 2.73s**.

- המשתמש הבחין בין `dict`, ‏`tuple`, ‏`dataclass` ו־Pydantic, ובנה
  `ActivatedUploadRequest` פנימי עם `frozen=True`. שירות ה־activation
  מחזיר כעת מאותה פעולת `UPDATE ... RETURNING` את המזהה וה־expiration,
  יחד עם ה־raw token שקיים בזיכרון בלבד. אימות ממוקד מחוץ לבידוד:
  **14 passed in 0.54s**; אימות מלא: **97 passed in 5.12s**.

- המשתמש בנה נכון מופע `UploadRequestActivationResponse` באמצעות keyword
  arguments עבור `upload_request_id`, ‏`upload_url` ו־`expires_at`. נוסף
  schema שמגביל את הסטטוס ל־`active` ומאמת את הקישור באמצעות `HttpUrl`.

- המשתמש זיהה נכון ש־`.env.example` נכנס ל־Git עם שמות משתנים וערכי
  דוגמה בלבד, בעוד `.env` האמיתי נשאר מחוץ ל־Git משום שהוא עשוי להכיל
  credentials ו־secrets. הוחלט לקרוא את `PUBLIC_BASE_URL` מהגדרות השרת
  ולא מכותרת `Host` הנשלטת בידי הלקוח. נוספה שכבת `Settings` מאומתת עם
  `pydantic-settings 2.16.2`; שתי בדיקות ההגדרות עברו, ולאחר מכן כל
  הסוויטה עברה מחוץ לבידוד: **95 passed in 2.97s**.

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
