# بک‌اند سامانه رزرو اقامتگاه (FastAPI + PostgreSQL)

پیاده‌سازی دیتابیس و APIهای اصلی سایت رزرو اقامتگاه بر اساس [ERD.md](ERD.md).
نیازی به فرانت‌اند ندارد؛ همه چیز از طریق **Swagger** (داخل مرورگر) یا **Postman** قابل تست است.

**فرانت‌اند «کلبه»** (Next.js): (Next.js): https://github.com/JamilZarei/kolbe — **نسخه آنلاین:** https://kolbe-ir.vercel.app

---

## ۱. ساختار پروژه

```
ReserveERD-backend/
├── ERD.md                      # نمودار ER
├── db/
│   ├── schema.sql              # ساخت جداول، کلیدها و قیدها (constraint)
│   └── seed.sql                # داده نمونه بومی ایران
├── app/
│   ├── main.py                 # نقطه شروع FastAPI
│   ├── config.py               # تنظیمات (از فایل .env)
│   ├── database.py             # اتصال SQLAlchemy
│   ├── models.py               # مدل‌های جداول
│   ├── schemas.py              # مدل‌های ورودی/خروجی (Pydantic)
│   ├── security.py / deps.py   # JWT، هش رمز، کنترل دسترسی
│   ├── services/booking.py     # منطق قیمت، موجودی، تخفیف، استرداد
│   └── routers/                # endpointها
├── scripts/init_db.py          # ساخت دیتابیس + اجرای schema و seed
├── tests/                      # تست خودکار end-to-end (pytest)
└── postman/Reserve-API.postman_collection.json
```

## ۲. طراحی دیتابیس (نکات مهم)

| مورد | پیاده‌سازی |
|---|---|
| جدول USER | به دلیل رزرو بودن کلمه `user` در PostgreSQL، نام جدول `app_user` است |
| یکتایی قیمت روزانه | `UNIQUE (unit_id, day)` روی `unit_price_calendar` |
| جلوگیری از رزرو هم‌پوشان | قید `EXCLUDE USING gist` روی `unit_id` + `daterange(check_in, check_out)` برای رزروهای `pending/confirmed` (افزونه `btree_gist`) — حتی اگر دو درخواست هم‌زمان برسند، دیتابیس اجازه نمی‌دهد |
| یک نظر برای هر رزرو | `review.booking_id UNIQUE` + فقط برای رزرو `completed` |
| اعتبارسنجی | `CHECK` برای نقش‌ها، وضعیت‌ها، امتیاز ۱ تا ۵، فرمت موبایل `09xxxxxxxxx`، `check_out > check_in` و … |
| مبالغ | به **تومان**، نوع `NUMERIC(14,0)` |

### داده نمونه (بومی و واقع‌نما)
- **۱۶ شهر واقعی** با استان صحیح: تهران، رامسر، نوشهر، کلاردشت، کاشان، اصفهان، ابیانه، خور، یزد، شیراز، کیش، قشم، ماسوله، بندر انزلی، تبریز، مشهد
- **۱۷ اقامتگاه** (ویلا استخردار نوشهر، بوم‌گردی بافت تاریخی کاشان، هتل سنتی فهادان یزد، کلبه ماسوله، هتل‌آپارتمان کیش و …) با آدرس و مختصات جغرافیایی واقعی منطقه — ۱۵ فعال، ۱ پیش‌نویس، ۱ تعلیق‌شده
- **۲۵ واحد** با قیمت‌های هم‌خوان با بازار ۱۴۰۵ (مثلاً ویلای استخردار شمال ۵٫۵ تا ۶٫۸ میلیون، اتاق بوم‌گردی ۱٫۶ تا ۲٫۹ میلیون تومان)
- **تقویم قیمت** آبان ۱۴۰۵ تا فروردین ۱۴۰۶: شب‌های پنجشنبه و جمعه ۲۵٪ گران‌تر، شب یلدا ۳۰٪، نوروز ۶۰٪
- **درگاه‌های پرداخت**: زرین‌پال، به‌پرداخت ملت، سامان کیش (سپ)، کیف پول
- **کدهای تخفیف**: `WELCOME1405`، `PAEEZ1405`، `YALDA1405`، `NOWRUZ1406`، `TABESTAN1405` (منقضی)
- رزروهای گذشته با نظر، رزروهای آینده، رزرو لغوشده با استرداد، پرداخت ناموفق، پیام‌های مهمان و میزبان

### کاربران آماده (رمز همه: `Pass@1234`)

| نقش | نام | ایمیل (username) | موبایل |
|---|---|---|---|
| ادمین | مدیر سامانه | `admin@reserve.test` | 09120000000 |
| میزبان | رضا احمدی (ویلاهای شمال) | `reza.ahmadi@reserve.test` | 09121234567 |
| میزبان | مریم کریمی (کاشان، ابیانه) | `maryam.karimi@reserve.test` | 09131456782 |
| میزبان | حسین رضایی (یزد، کویر مصر) | `hossein.rezaei@reserve.test` | 09133521478 |
| مهمان | علی محمدی | `ali.mohammadi@reserve.test` | 09123458901 |
| مهمان | زهرا حسینی | `zahra.hosseini@reserve.test` | 09351237846 |
| مهمان | سعید نوری (رزرو ۸ را تمام کرده و هنوز نظر نداده) | `saeed.nouri@reserve.test` | 09141175386 |

---

### داده نمونه گسترده (seed_extra.sql)
`scripts/gen_seed_extra.py` فایل `db/seed_extra.sql` را می‌سازد: **۲۰۰ اقامتگاه در ۴۰ شهر** (هتل‌های شناخته‌شده، هتل سنتی، بوم‌گردی، ویلا، کلبه، آپارتمان)، حدود ۴۰۰ واحد با قیمت‌های بازار ۱۴۰۵، حدود ۱۰۰۰ رزرو، ۶۰۰ نظر، و عکس‌های مرتبط با هر شهر (`uploads/seed`، منبع در `CREDITS.md`).
`python scripts/init_db.py` همه را اعمال می‌کند؛ `--no-extra` فقط داده پایه را می‌سازد (تست‌ها از همین استفاده می‌کنند).

## ۳. نصب و اجرا (قدم‌به‌قدم)

### پیش‌نیازها
1. **Python 3.11 یا بالاتر** — از python.org
2. **PostgreSQL 14 یا بالاتر** — از postgresql.org/download/windows (هنگام نصب برای کاربر `postgres` رمز `postgres` بگذارید، یا رمز دلخواه را بعداً در `.env` وارد کنید)

### مراحل (در PowerShell داخل پوشه پروژه)

```powershell
# 1) ساخت محیط مجازی و نصب کتابخانه‌ها
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) تنظیمات: فایل .env را از روی نمونه بسازید و در صورت نیاز رمز دیتابیس را عوض کنید
copy .env.example .env

# 3) ساخت دیتابیس reserve_db + جداول + داده نمونه
python scripts/init_db.py

# 4) اجرای سرور
uvicorn app.main:app --reload
```

> اگر `Activate.ps1` خطای Execution Policy داد، یک بار اجرا کنید:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

وقتی پیام `Uvicorn running on http://127.0.0.1:8000` را دیدید، سرور آماده است.
برای بازگرداندن دیتابیس به حالت اولیه، دوباره `python scripts/init_db.py` را اجرا کنید.

---

## ۴. راهنمای تست برای کاربر مبتدی

### روش الف: Swagger (ساده‌ترین، بدون نصب برنامه)

1. سرور را اجرا کنید و در مرورگر بروید به: **http://127.0.0.1:8000/docs**
2. فهرست همه APIها گروه‌بندی‌شده نمایش داده می‌شود.
3. **تست یک API عمومی (بدون ورود):**
   - روی `GET /cities` کلیک کنید ← دکمه **Try it out** ← دکمه آبی **Execute**
   - پایین‌تر در بخش **Response body** فهرست شهرها و در **Code** عدد `200` (یعنی موفق) را می‌بینید.
4. **ورود (گرفتن توکن):**
   - بالای صفحه دکمه سبز **Authorize** 🔓 را بزنید.
   - در `username` بنویسید `ali.mohammadi@reserve.test` و در `password` بنویسید `Pass@1234` ← **Authorize** ← **Close**
   - حالا قفل‌ها بسته 🔒 شده‌اند و درخواست‌ها با هویت «علی محمدی» ارسال می‌شوند.
5. **سناریوی کامل رزرو:**

   | گام | API | ورودی | نتیجه مورد انتظار |
   |---|---|---|---|
   | ۱ | `GET /properties` | `city` = `کاشان` | اقامتگاه شماره 4 |
   | ۲ | `GET /properties/{property_id}` | `4` | جزئیات، واحدها (5، 6، 7)، امکانات، امتیاز |
   | ۳ | `GET /units/{unit_id}/quote` | unit_id=`6`، تاریخ ورود/خروج آینده (مثلاً `2027-01-10` و `2027-01-13`)، guests=`2`، coupon_code=`WELCOME1405` | قیمت هر شب، تخفیف، مبلغ نهایی |
   | ۴ | `POST /bookings` | بدنه پایین | کد `201` و `"status": "pending"` — عدد `id` را یادداشت کنید |
   | ۵ | `POST /bookings/{booking_id}/pay` | `{"method": "zarinpal"}` | `"status": "paid"` |
   | ۶ | `GET /bookings/{booking_id}` | همان id | `"status": "confirmed"` |
   | ۷ | `POST /bookings/{booking_id}/cancel` | همان id | لغو و مبلغ استرداد طبق قانون لغو |

   بدنه گام ۴:
   ```json
   {
     "unit_id": 6,
     "check_in": "2027-01-10",
     "check_out": "2027-01-13",
     "guests_count": 2,
     "coupon_code": "WELCOME1405"
   }
   ```
6. **تست خطاها (به همان اندازه مهم است):**
   - گام ۴ را دوباره با همان تاریخ‌ها اجرا کنید ← کد `409` (واحد قبلاً رزرو شده)
   - `guests_count` را `10` بگذارید ← کد `400` (بیش از ظرفیت)
   - Authorize ← **Logout** و یک API نیازمند ورود را صدا بزنید ← کد `401`
   - با کاربر مهمان `GET /users` را بزنید ← کد `403` (فقط ادمین)
7. **تست نقش میزبان:** Logout کنید و با `reza.ahmadi@reserve.test` وارد شوید؛ سپس `GET /properties/mine` و `GET /bookings/hosting` را اجرا کنید.
8. **ثبت نظر:** با `saeed.nouri@reserve.test` وارد شوید و `POST /bookings/8/review` را با `{"rating": 5, "comment": "عالی بود"}` بزنید.

#### معنی کدهای پاسخ
| کد | معنی |
|---|---|
| 200 / 201 | موفق / ساخته شد |
| 204 | موفق، بدون محتوا (مثلاً حذف) |
| 400 | داده ورودی منطقی نیست (تاریخ گذشته، ظرفیت، کد تخفیف نامعتبر) |
| 401 | وارد نشده‌اید یا توکن منقضی شده |
| 403 | اجازه این کار را ندارید |
| 404 | پیدا نشد |
| 409 | تداخل (رزرو تکراری، وضعیت نامناسب) |
| 422 | فرمت ورودی اشتباه است (مثلاً موبایل ۱۱ رقمی نیست) — جزئیات خطا در پاسخ آمده |

### روش ب: Postman

1. Postman را از postman.com/downloads نصب و اجرا کنید (ورود به حساب اختیاری است).
2. **Import** (بالا سمت چپ) ← فایل `postman/Reserve-API.postman_collection.json` را بکشید و رها کنید.
3. در سمت چپ کالکشن **Reserve API** با ۷ پوشه ظاهر می‌شود. آدرس سرور در متغیر `baseUrl` تنظیم شده است (روی نام کالکشن ← تب **Variables**).
4. **اجرای دستی:** ابتدا پوشه **1. احراز هویت** ← درخواست `Login - مهمان` را باز کنید و **Send** بزنید. توکن به‌صورت خودکار در متغیر `guestToken` ذخیره می‌شود و بقیه درخواست‌ها از آن استفاده می‌کنند. همین کار را برای Login میزبان و ادمین انجام دهید.
5. سپس درخواست‌های پوشه **3. فرایند رزرو** را به ترتیب از بالا به پایین Send کنید. شناسه رزرو ساخته‌شده خودکار در `bookingId` ذخیره می‌شود.
6. **اجرای خودکار همه:** روی نام کالکشن کلیک راست ← **Run collection** ← **Run Reserve API**. Postman همه درخواست‌ها را به ترتیب اجرا می‌کند و نتیجه تست‌ها (سبز = موفق، قرمز = ناموفق) را نشان می‌دهد.
7. نتیجه هر درخواست در تب **Test Results** پایین صفحه دیده می‌شود.

> نکته: اجرای دوم پوشه ۵ ممکن است برای «افزودن شهر» در پوشه ادمین خطای 409 بدهد چون شهر قبلاً اضافه شده؛ این رفتار درست است. برای شروع تمیز، `python scripts/init_db.py` را اجرا کنید.

### روش ج: تست خودکار با pytest (برای توسعه‌دهنده)

```powershell
pytest -v
```
این دستور یک دیتابیس جداگانه به نام `reserve_test` می‌سازد (دیتابیس اصلی دست نمی‌خورد) و بیش از ۳۰ سناریو را تست می‌کند: ورود، جستجو، قیمت‌گذاری، تداخل رزرو، پرداخت، لغو و استرداد، نظر، پنل میزبان، دسترسی‌ها.

---

## ۵. فهرست APIها

| گروه | Method و مسیر | دسترسی |
|---|---|---|
| احراز هویت | `POST /auth/register`، `POST /auth/login`، `GET/PATCH /auth/me` | عمومی / کاربر |
| کاربران | `GET /users`، `GET /users/{id}` | ادمین |
| اطلاعات پایه | `GET/POST /cities`، `/property-types`، `/amenities`، `/cancellation-policies` | GET عمومی، POST ادمین |
| اقامتگاه | `GET /properties` (جستجو: شهر، استان، نوع، ظرفیت، تاریخ، قیمت، امکانات، مرتب‌سازی) | عمومی |
| | `GET /properties/{id}`، `GET /properties/{id}/reviews`، `GET /properties/{id}/units` | عمومی |
| | `POST /properties`، `PATCH/DELETE /properties/{id}`، `GET /properties/mine` | میزبان |
| | `PUT /properties/{id}/amenities`، `POST /properties/{id}/photos`، `DELETE /photos/{id}`، `POST /properties/{id}/units` | میزبان |
| واحد و تقویم | `GET/PATCH/DELETE /units/{id}`، `GET/PUT /units/{id}/calendar`، `GET /units/{id}/quote` | GET عمومی |
| رزرو | `POST /bookings`، `GET /bookings/me`، `GET /bookings/{id}` | کاربر |
| | `POST /bookings/{id}/pay`، `/cancel`، `/review`، `GET /bookings/{id}/payments` | مهمان رزرو |
| | `GET /bookings/hosting`، `POST /bookings/{id}/complete` | میزبان / ادمین |
| تخفیف | `GET/POST /coupons`، `GET /coupons/{code}/check` | ادمین / کاربر |
| علاقه‌مندی | `GET /favorites`، `POST/DELETE /favorites/{property_id}` | کاربر |
| پیام | `POST /messages`، `GET /messages?with_user_id=&booking_id=` | کاربر |
| پنل ادمین | `GET /admin/stats`، `PATCH /users/{id}` (تغییر نقش) | ادمین |
| عکس | `POST /properties/{id}/photos/upload` (multipart، jpg/png/webp تا ۵MB)، `PATCH /photos/{id}` (کاور/ترتیب) | میزبان/ادمین |

> فهرست‌های `GET /properties`، `GET /users` و `GET /bookings/hosting` تعداد کل را در هدر `X-Total-Count` برمی‌گردانند. فایل‌های آپلودی از مسیر `/uploads/...` سرو می‌شوند.

### چرخه وضعیت رزرو
```
pending ──(پرداخت موفق)──► confirmed ──(پس از تاریخ خروج، میزبان)──► completed ──► امکان ثبت نظر
   │                           │
   └──────(لغو)──────► cancelled ◄──(لغو + استرداد طبق قانون لغو)
```
**محاسبه استرداد:** اگر مهمان حداقل `free_cancel_days` روز قبل از ورود لغو کند، کل مبلغ؛ وگرنه `refund_percent` درصد برمی‌گردد. لغو توسط میزبان همیشه استرداد کامل دارد.

## انتشار روی Vercel

API روی https://kolbe-ir-api.vercel.app (پروژه `kolbe-ir-api`) منتشر شده است:
- **دیتابیس:** Neon Postgres از Vercel Marketplace؛ `DATABASE_URL` خودکار تنظیم می‌شود (`postgres://` به `postgresql+psycopg://` تبدیل می‌شود و روی Vercel از `NullPool` استفاده می‌شود). پر کردن دیتابیس: `DATABASE_URL=<DATABASE_URL_UNPOOLED> python scripts/init_db.py`.
- **عکس‌ها:** عکس‌های نمونه در `public/uploads/seed` از CDN سرو می‌شوند؛ عکس‌های آپلودی وقتی `BLOB_READ_WRITE_TOKEN` موجود باشد در Vercel Blob ذخیره می‌شوند (`app/storage.py`) و در حالت محلی روی دیسک.
- **متغیرها:** `JWT_SECRET` (تصادفی)، `CORS_ORIGINS=https://kolbe-ir.vercel.app`.
- **انتشار مجدد:** `powershell -File scripts\deploy_vercel.ps1`
