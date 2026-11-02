# ERD سایت رزرو اقامتگاه

```mermaid
erDiagram
    USER {
        int id PK
        string full_name
        string email UK
        string phone UK
        string password_hash
        string role "guest | host | admin"
        datetime created_at
    }
    CITY {
        int id PK
        string name
        string province
        string country
    }
    PROPERTY_TYPE {
        int id PK
        string name "ویلا، هتل، سوئیت، کلبه ..."
    }
    CANCELLATION_POLICY {
        int id PK
        string name
        int free_cancel_days
        decimal refund_percent
    }
    PROPERTY {
        int id PK
        int host_id FK
        int city_id FK
        int type_id FK
        int policy_id FK
        string title
        text description
        string address
        decimal latitude
        decimal longitude
        time check_in_time
        time check_out_time
        string status "draft | active | suspended"
    }
    UNIT {
        int id PK
        int property_id FK
        string name
        int max_guests
        int bedrooms
        int beds
        int bathrooms
        decimal base_price_per_night
    }
    UNIT_PRICE_CALENDAR {
        int id PK
        int unit_id FK
        date day
        decimal price
        boolean is_available
    }
    AMENITY {
        int id PK
        string name "وای‌فای، پارکینگ، استخر ..."
        string icon
    }
    PROPERTY_AMENITY {
        int property_id PK, FK
        int amenity_id PK, FK
    }
    PHOTO {
        int id PK
        int property_id FK
        int unit_id FK "nullable"
        string url
        int sort_order
    }
    BOOKING {
        int id PK
        int guest_id FK
        int unit_id FK
        int coupon_id FK "nullable"
        date check_in
        date check_out
        int guests_count
        decimal total_price
        string status "pending | confirmed | cancelled | completed"
        datetime created_at
    }
    PAYMENT {
        int id PK
        int booking_id FK
        decimal amount
        string method
        string status "paid | failed | refunded"
        string transaction_ref
        datetime paid_at
    }
    COUPON {
        int id PK
        string code UK
        decimal discount_percent
        date valid_from
        date valid_to
        int usage_limit
    }
    REVIEW {
        int id PK
        int booking_id FK, UK
        int rating "1-5"
        text comment
        datetime created_at
    }
    FAVORITE {
        int user_id PK, FK
        int property_id PK, FK
    }
    MESSAGE {
        int id PK
        int sender_id FK
        int receiver_id FK
        int booking_id FK "nullable"
        text body
        datetime sent_at
    }

    USER ||--o{ PROPERTY : "میزبان است"
    USER ||--o{ BOOKING : "رزرو می‌کند"
    USER ||--o{ FAVORITE : "علاقه‌مندی"
    USER ||--o{ MESSAGE : "ارسال می‌کند (sender_id)"
    USER ||--o{ MESSAGE : "دریافت می‌کند (receiver_id)"
    UNIT |o--o{ PHOTO : "عکس اختصاصی واحد (unit_id)"
    CITY ||--o{ PROPERTY : "واقع در"
    PROPERTY_TYPE ||--o{ PROPERTY : "نوع"
    CANCELLATION_POLICY ||--o{ PROPERTY : "قوانین لغو"
    PROPERTY ||--|{ UNIT : "دارد"
    PROPERTY ||--o{ PHOTO : "دارد"
    PROPERTY ||--o{ PROPERTY_AMENITY : ""
    AMENITY ||--o{ PROPERTY_AMENITY : ""
    PROPERTY ||--o{ FAVORITE : ""
    UNIT ||--o{ UNIT_PRICE_CALENDAR : "قیمت/موجودی روزانه"
    UNIT ||--o{ BOOKING : "رزرو می‌شود"
    BOOKING ||--o{ PAYMENT : "پرداخت"
    BOOKING ||--o| REVIEW : "نظر"
    COUPON |o--o{ BOOKING : "اعمال می‌شود (coupon_id اختیاری)"
    BOOKING |o--o{ MESSAGE : "گفتگو (booking_id اختیاری)"
```

## نکات طراحی
- **PROPERTY در برابر UNIT**: اقامتگاه (مثلاً هتل) می‌تواند چند واحد/اتاق داشته باشد؛ رزرو روی UNIT انجام می‌شود.
- **UNIT_PRICE_CALENDAR**: قیمت و موجودی هر روز جدا نگهداری می‌شود (تعطیلات، فصل پرتردد، مسدودسازی).
- روی `UNIT_PRICE_CALENDAR` ترکیب `unit_id + day` باید یکتا باشد تا یک واحد برای یک روز دو قیمت نداشته باشد.
- **PROPERTY_AMENITY / FAVORITE**: جداول واسط برای رابطه چند‌به‌چند.
- **REVIEW** با `booking_id` یکتا: فقط مهمانی که واقعاً اقامت داشته می‌تواند یک نظر ثبت کند.
- جلوگیری از رزرو هم‌پوشان باید در لایه برنامه/دیتابیس (constraint یا تراکنش) روی `unit_id + بازه تاریخ` اعمال شود.
