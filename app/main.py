from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import ON_VERCEL, settings, uploads_path
from app.database import engine
from app.routers import admin, auth, bookings, catalog, misc, properties, units

app = FastAPI(
    title="API کلبه — سامانه رزرو اقامتگاه",
    version="1.0.0",
    description=(
        "بک‌اند سایت رزرو اقامتگاه (ویلا، سوئیت، بوم‌گردی، هتل) بر اساس ERD پروژه.\n\n"
        "**ورود سریع برای تست:** دکمه Authorize را بزنید؛ username = `ali.mohammadi@reserve.test` "
        "و password = `Pass@1234`.\n\n"
        "مبالغ به **تومان** و تاریخ‌ها به میلادی (YYYY-MM-DD) هستند."
    ),
    docs_url=None,
)

# Persian text in Swagger runs right-to-left; paths and code stay left-to-right
RTL_STYLE = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap">
<style>
  .swagger-ui, .swagger-ui .info .title, .swagger-ui .opblock-tag { font-family: Vazirmatn, Tahoma, sans-serif; }
  .swagger-ui .info, .swagger-ui .info .description .markdown p,
  .swagger-ui .opblock-tag, .swagger-ui .opblock-description-wrapper p,
  .swagger-ui .parameter__name, .swagger-ui .parameters-col_description .markdown p,
  .swagger-ui .response-col_description .markdown p, .swagger-ui .responses-inner h4,
  .swagger-ui .opblock-section-header h4 { direction: rtl; text-align: right; }
  .swagger-ui .opblock .opblock-summary-description { direction: rtl; text-align: right; flex: 1; padding: 0 12px; }
  .swagger-ui .opblock-summary-path, .swagger-ui code, .swagger-ui pre, .swagger-ui .microlight,
  .swagger-ui .info .title small { direction: ltr; unicode-bidi: isolate; }
</style>
"""


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> HTMLResponse:
    page = get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} - Swagger",
                               swagger_ui_parameters={"persistAuthorization": True})
    return HTMLResponse(page.body.decode().replace("</head>", RTL_STYLE + "</head>"))


app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["X-Total-Count"])

# Uploaded photos (and the seed photos) are served from /uploads. On Vercel the seed photos are deployed
# under public/uploads (served by the CDN) and new uploads go to Vercel Blob, so nothing is mounted there.
if not ON_VERCEL:
    UPLOADS = uploads_path()
    UPLOADS.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")

for r in (auth.router, catalog.router, properties.router, units.router, bookings.router,
          misc.coupons, misc.favorites, misc.messages, admin.router):
    app.include_router(r)


@app.get("/health", tags=["سلامت سرویس"], summary="بررسی اتصال به دیتابیس")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
