"""Generate db/seed_extra.sql: ~185 more properties across Iran (200 in total), with units, photos,
amenities, hosts, guests, bookings, payments and reviews.

The output is deterministic (fixed random seed), so re-running this script produces the same file.
Usage:  python scripts/gen_seed_extra.py
Then:   python scripts/init_db.py          (applies schema.sql + seed.sql + seed_extra.sql)

Photos: city/heritage photos are from Wikimedia Commons (see uploads/seed/CREDITS.md) and are served
by this backend at /uploads/seed/...; interior/villa/resort photos are Unsplash CDN links.
"""
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PHOTOS = ROOT / "uploads" / "seed"
rnd = random.Random(1405)

# ----------------------------------------------------------------------------- cities
# key, name, province, lat, lon, region (existing ids 1..16 are in seed.sql)
EXISTING_CITIES = {
    1: ("tehran", "تهران", 35.6997, 51.3380, "metro"), 2: ("ramsar", "رامسر", 36.9031, 50.6583, "north"),
    3: ("nowshahr", "نوشهر", 36.6487, 51.4960, "north"), 4: ("kelardasht", "کلاردشت", 36.5050, 51.1450, "forest"),
    5: ("kashan", "کاشان", 33.9850, 51.4100, "heritage"), 6: ("isfahan", "اصفهان", 32.6539, 51.6660, "heritage"),
    7: ("abyaneh", "ابیانه", 33.5770, 51.6040, "village"), 8: ("khur", "خور", 33.7750, 55.0830, "desert"),
    9: ("yazd", "یزد", 31.8974, 54.3569, "heritage"), 10: ("shiraz", "شیراز", 29.6100, 52.5425, "heritage"),
    11: ("kish", "کیش", 26.5390, 53.9800, "island"), 12: ("qeshm", "قشم", 26.9580, 56.2700, "island"),
    13: ("masuleh", "ماسوله", 37.1550, 48.9870, "village"), 14: ("anzali", "بندر انزلی", 37.4720, 49.4620, "north"),
    15: ("tabriz", "تبریز", 38.0800, 46.2919, "metro"), 16: ("mashhad", "مشهد", 36.2970, 59.6060, "metro"),
}
NEW_CITIES = [
    ("chalus", "چالوس", "مازندران", 36.6550, 51.4200, "north"),
    ("rasht", "رشت", "گیلان", 37.2808, 49.5832, "north"),
    ("lahijan", "لاهیجان", "گیلان", 37.2072, 50.0039, "north"),
    ("sareyn", "سرعین", "اردبیل", 38.1500, 48.0700, "mountain"),
    ("hamadan", "همدان", "همدان", 34.7990, 48.5150, "city"),
    ("kerman", "کرمان", "کرمان", 30.2839, 57.0834, "city"),
    ("kermanshah", "کرمانشاه", "کرمانشاه", 34.3142, 47.0650, "city"),
    ("qazvin", "قزوین", "قزوین", 36.2688, 50.0041, "city"),
    ("zanjan", "زنجان", "زنجان", 36.6736, 48.4787, "city"),
    ("bushehr", "بوشهر", "بوشهر", 28.9234, 50.8203, "south"),
    ("hormuz", "جزیره هرمز", "هرمزگان", 27.0600, 56.4600, "island"),
    ("bandarabbas", "بندرعباس", "هرمزگان", 27.1832, 56.2666, "south"),
    ("chabahar", "چابهار", "سیستان و بلوچستان", 25.2919, 60.6430, "south"),
    ("gorgan", "گرگان", "گلستان", 36.8456, 54.4393, "forest"),
    ("sanandaj", "سنندج", "کردستان", 35.3114, 46.9960, "city"),
    ("khorramabad", "خرم‌آباد", "لرستان", 33.4878, 48.3558, "city"),
    ("kandovan", "کندوان", "آذربایجان شرقی", 37.7950, 46.2480, "village"),
    ("meybod", "میبد", "یزد", 32.2501, 54.0166, "desert"),
    ("shushtar", "شوشتر", "خوزستان", 32.0455, 48.8567, "heritage"),
    ("urmia", "ارومیه", "آذربایجان غربی", 37.5527, 45.0761, "city"),
    ("filband", "فیلبند", "مازندران", 36.0270, 52.4900, "forest"),
    ("lavasan", "لواسان", "تهران", 35.8230, 51.6330, "mountain"),
    ("shahmirzad", "شهمیرزاد", "سمنان", 35.7730, 53.3290, "mountain"),
    ("marivan", "مریوان", "کردستان", 35.5180, 46.1760, "mountain"),
]
CITY = {}  # key -> dict(id, name, province, lat, lon, region)
PROVINCES = {1: "تهران", 2: "مازندران", 3: "مازندران", 4: "مازندران", 5: "اصفهان", 6: "اصفهان", 7: "اصفهان",
             8: "اصفهان", 9: "یزد", 10: "فارس", 11: "هرمزگان", 12: "هرمزگان", 13: "گیلان", 14: "گیلان",
             15: "آذربایجان شرقی", 16: "خراسان رضوی"}
for cid, (key, name, lat, lon, region) in EXISTING_CITIES.items():
    CITY[key] = dict(id=cid, name=name, province=PROVINCES[cid], lat=lat, lon=lon, region=region)
for i, (key, name, prov, lat, lon, region) in enumerate(NEW_CITIES, start=17):
    CITY[key] = dict(id=i, name=name, province=prov, lat=lat, lon=lon, region=region)

# Local attractions used in descriptions
SIGHTS = {
    "tehran": ["برج میلاد", "کاخ گلستان", "پل طبیعت", "بازار بزرگ تهران", "دربند"],
    "ramsar": ["تله‌کابین رامسر", "کاخ‌موزه رامسر", "جواهرده", "ساحل رامسر"],
    "nowshahr": ["ساحل نوشهر", "باغ گیاه‌شناسی نوشهر", "جاده چالوس"],
    "kelardasht": ["دریاچه ولشت", "روستای مکارود", "تخت سلیمان"],
    "kashan": ["خانه طباطبایی‌ها", "باغ فین", "حمام سلطان امیراحمد", "خانه بروجردی‌ها"],
    "isfahan": ["میدان نقش جهان", "سی‌وسه‌پل", "مسجد شیخ لطف‌الله", "کاخ چهلستون", "محله جلفا"],
    "abyaneh": ["خانه‌های گلی سرخ ابیانه", "مسجد جامع ابیانه", "کوه کرکس"],
    "khur": ["کویر مصر", "تپه‌های شنی رملی", "روستای گرمه"],
    "yazd": ["مسجد جامع یزد", "باغ دولت‌آباد", "مجموعه امیرچخماق", "آتشکده یزد", "بادگیرهای فهادان"],
    "shiraz": ["باغ ارم", "مسجد نصیرالملک", "حافظیه", "ارگ کریم‌خان", "تخت جمشید"],
    "kish": ["کشتی یونانی", "اسکله تفریحی", "بازار مریم", "ساحل مرجان", "شهر زیرزمینی کاریز"],
    "qeshm": ["دره ستارگان", "جنگل حرا", "غار نمکدان", "روستای لافت"],
    "masuleh": ["بافت پلکانی ماسوله", "آبشار کوشم", "قلعه رودخان"],
    "anzali": ["تالاب انزلی", "ساحل غازیان", "بازار ماهی‌فروشان"],
    "tabriz": ["بازار سرپوشیده تبریز", "ائل‌گلی", "ارگ علیشاه", "مسجد کبود"],
    "mashhad": ["حرم امام رضا (ع)", "آرامگاه فردوسی", "کوهسنگی", "طرقبه و شاندیز"],
    "chalus": ["جاده چالوس", "تله‌کابین نمک‌آبرود", "ساحل چالوس"],
    "rasht": ["میدان شهرداری رشت", "بازار رشت", "موزه میراث روستایی گیلان"],
    "lahijan": ["باغ‌های چای لاهیجان", "استخر لاهیجان", "شیطان‌کوه"],
    "sareyn": ["چشمه‌های آب‌گرم سرعین", "کوه سبلان", "تله‌کابین آلوارس"],
    "hamadan": ["غار علیصدر", "گنجنامه", "آرامگاه بوعلی سینا", "تپه هگمتانه"],
    "kerman": ["مجموعه گنجعلی‌خان", "باغ شاهزاده ماهان", "کویر لوت", "بازار وکیل کرمان"],
    "kermanshah": ["طاق‌بستان", "کتیبه بیستون", "تکیه معاون‌الملک"],
    "qazvin": ["کاخ چهلستون قزوین", "قلعه الموت", "دریاچه اوان"],
    "zanjan": ["گنبد سلطانیه", "رختشویخانه زنجان", "معبد داش‌کسن"],
    "bushehr": ["بافت تاریخی بوشهر", "عمارت ملک", "ساحل بوشهر"],
    "hormuz": ["ساحل سرخ هرمز", "دره رنگین‌کمان", "قلعه پرتغالی‌ها"],
    "bandarabbas": ["اسکله شهید حقانی", "بازار ماهی بندرعباس", "معبد هندوها"],
    "chabahar": ["ساحل دریای عمان", "کوه‌های مریخی", "ساحل درک"],
    "gorgan": ["جنگل ناهارخوران", "پارک ملی گلستان", "آبشار کبودوال"],
    "sanandaj": ["عمارت آصف وزیری", "روستای پالنگان", "اورامان تخت"],
    "khorramabad": ["قلعه فلک‌الافلاک", "آبشار بیشه", "دریاچه کیو"],
    "kandovan": ["خانه‌های صخره‌ای کندوان", "چشمه معدنی کندوان", "کوه سهند"],
    "meybod": ["قلعه نارین", "یخچال خشتی میبد", "کاروانسرای شاه‌عباسی"],
    "shushtar": ["سازه‌های آبی شوشتر", "پل بند شادروان", "زیگورات چغازنبیل"],
    "urmia": ["دریاچه ارومیه", "کلیسای مریم مقدس", "بند ارومیه"],
    "filband": ["دریای ابر فیلبند", "جنگل‌های هیرکانی", "روستای اروست"],
    "lavasan": ["سد لتیان", "جاده فشم", "کوه‌های شمال تهران"],
    "shahmirzad": ["جنگل ابر", "باغ‌های گردو", "کوه‌های البرز شرقی"],
    "marivan": ["دریاچه زریوار", "جنگل‌های بلوط زاگرس", "بازارچه مرزی"],
}

# ----------------------------------------------------------------------------- photos
UNSPLASH = {  # categories checked visually against a contact sheet
    "resort": ["1566073771259-6a8506099945", "1551882547-ff40c63fe5fa", "1571896349842-33c89424de2d",
               "1520250497591-112f2f40a3f4", "1542314831-068cd1dbfeeb", "1564501049412-61c2a3083791",
               "1540541338287-41700207dee6", "1584132967334-10e028bd69f7", "1561501900-3701fa6a0864",
               "1600011689032-8b628b8a8747", "1602002418082-a4443e081dd1"],
    "hotel": ["1455587734955-081b22074882", "1568084680786-a84f91d1153c",
              "1535827841776-24afc1e255ac", "1615460549969-36fa19521a4f"],
    "room": ["1582719478250-c89cae4dc85b", "1611892440504-42a792e24d32", "1590490360182-c33d57733427",
             "1631049307264-da0ec9d70304", "1618773928121-c32242e63f39", "1595576508898-0ad5c879a061",
             "1505693416388-ac5ce068fe85", "1578683010236-d716f9a3f461"],
    "villa": ["1613490493576-7fde63acd811", "1580587771525-78b9dba3b914", "1512917774080-9991f1c4c750",
              "1600596542815-ffad4c1539a9", "1600585154340-be6161a56a0c"],
    "cabin": ["1449158743715-0a90ebb6d2d8", "1510798831971-661eb04b3739", "1518780664697-55e3ad937233",
              "1587061949409-02df41d5e562"],
    "apartment": ["1522708323590-d24dbb6b0267", "1502672260266-1c1ef2d93688", "1560448204-e02f11c3d0e2",
                  "1586023492125-27b2c045efd7"],
}


def unsplash(pid: str) -> str:
    return f"https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w=1200&q=75"


LOCAL = {}  # topic -> list of /uploads/seed urls (only files that exist and were not rejected)
REJECTED = set(json.loads((SEED_PHOTOS / "rejected.json").read_text(encoding="utf-8"))) \
    if (SEED_PHOTOS / "rejected.json").exists() else set()
for f in sorted(SEED_PHOTOS.glob("*.jpg")):
    if f.stem in REJECTED:
        continue
    topic = f.stem.rsplit("_", 1)[0]
    LOCAL.setdefault(topic, []).append(f"/uploads/seed/{f.name}")

# Heritage-style photos for traditional hotels / eco-lodges when a city has none of its own
HERITAGE_FALLBACK = ["trad_yazd", "trad_kashan", "trad_isfahan", "trad_shiraz", "courtyard", "yazd", "kashan"]
DESERT_FALLBACK = ["garmeh"]
FOREST_FALLBACK = ["forest"]
SEA_FALLBACK = ["caspian"]


def pick_local(*topics: str) -> str | None:
    pool = [u for t in topics for u in LOCAL.get(t, [])]
    return rnd.choice(pool) if pool else None


def pick_unsplash(cat: str, avoid: set) -> str:
    options = [p for p in UNSPLASH[cat] if unsplash(p) not in avoid] or UNSPLASH[cat]
    return unsplash(rnd.choice(options))


def photos_for(kind: str, city_key: str) -> list[str]:
    """Cover photo matches the property type; then a city photo; then interior shots."""
    region = CITY[city_key]["region"]
    urls: list[str] = []

    def add(url):
        if url and url not in urls:
            urls.append(url)

    if kind in ("hotel5", "hotel4", "hotel3"):
        add(pick_unsplash("resort" if region in ("island", "south") else "hotel", set(urls)))
        add(pick_local(city_key))
        add(pick_unsplash("room", set(urls)))
        add(pick_unsplash("room", set(urls)))
        if kind == "hotel5":
            add(pick_unsplash("resort", set(urls)))
    elif kind == "traditional":
        # Only photos of the property's own city; another city's landmark would be misleading
        own = [f"trad_{city_key}", city_key]
        if LOCAL.get(own[0]) or LOCAL.get(own[1]):
            add(pick_local(own[0]) or pick_local(own[1]))
            add(pick_local(*own))
            add(pick_local(*own))
        else:
            add(pick_local("courtyard"))
        add(pick_unsplash("room", set(urls)))
    elif kind in ("ecolodge", "rural"):
        fallback = DESERT_FALLBACK if region == "desert" else FOREST_FALLBACK if region in ("forest", "north") \
            else ["courtyard", "garmeh"]
        # Own-city photos first; regional fallbacks (desert / forest) only when the city has none
        if LOCAL.get(city_key):
            add(pick_local(city_key))
            add(pick_local(city_key))
            add(pick_local(city_key))
        else:
            add(pick_local(*fallback))
            add(pick_local(*fallback))
        add(pick_unsplash("room", set(urls)))
    elif kind in ("villa", "villa_lux"):
        add(pick_unsplash("villa", set(urls)))
        add(pick_local(city_key) or pick_local(*(SEA_FALLBACK if region == "north" else FOREST_FALLBACK)))
        add(pick_unsplash("apartment", set(urls)))
        add(pick_unsplash("room", set(urls)))
    elif kind == "cabin":
        add(pick_unsplash("cabin", set(urls)))
        add(pick_local(city_key) or pick_local(*FOREST_FALLBACK))
        add(pick_unsplash("cabin", set(urls)))
        add(pick_unsplash("room", set(urls)))
    elif kind == "hotel_apartment":
        add(pick_unsplash("resort", set(urls)))
        add(pick_local(city_key))
        add(pick_unsplash("apartment", set(urls)))
        add(pick_unsplash("room", set(urls)))
    else:  # apartment / suite
        add(pick_unsplash("apartment", set(urls)))
        add(pick_local(city_key))
        add(pick_unsplash("apartment", set(urls)))
        add(pick_unsplash("room", set(urls)))
    return urls


# ----------------------------------------------------------------------------- people
FIRST_M = ["امیر", "محمدرضا", "حامد", "بهزاد", "کاوه", "پویا", "مهران", "آرش", "یاسر", "مسعود", "فرهاد", "سینا",
           "بابک", "رامین", "شهرام", "علیرضا", "مجید", "نیما"]
FIRST_F = ["مینا", "شیوا", "پریسا", "مهسا", "لیلا", "ترانه", "سمیرا", "نازنین", "یگانه", "هانیه", "آزاده", "رویا",
           "فرناز", "شیرین", "مریم", "کیمیا"]
LAST = ["رستمی", "شریفی", "توکلی", "فرهادی", "بهرامی", "کرمانی", "یزدانی", "شیرازی", "تهرانی", "گیلانی",
        "نیک‌نام", "پاکزاد", "زمانی", "امینی", "سلطانی", "حیدری", "عباسی", "مرادی", "صالحی", "یوسفی", "خسروی",
        "اسدی", "طاهری", "نظری", "کیانی", "جلالی", "فتحی", "شکوهی"]
LATIN = {"امیر": "amir", "محمدرضا": "mohammadreza", "حامد": "hamed", "بهزاد": "behzad", "کاوه": "kaveh",
         "پویا": "pouya", "مهران": "mehran", "آرش": "arash", "یاسر": "yaser", "مسعود": "masoud", "فرهاد": "farhad",
         "سینا": "sina", "بابک": "babak", "رامین": "ramin", "شهرام": "shahram", "علیرضا": "alireza", "مجید": "majid",
         "نیما": "nima", "مینا": "mina", "شیوا": "shiva", "پریسا": "parisa", "مهسا": "mahsa", "لیلا": "leila",
         "ترانه": "taraneh", "سمیرا": "samira", "نازنین": "nazanin", "یگانه": "yeganeh", "هانیه": "hanieh",
         "آزاده": "azadeh", "رویا": "roya", "فرناز": "farnaz", "شیرین": "shirin", "مریم": "maryam", "کیمیا": "kimia"}

users = []  # (id, name, email, phone, role, created_at)
used_names = set()


def new_person(uid: int, role: str, created: datetime) -> tuple:
    while True:
        first = rnd.choice(FIRST_M + FIRST_F)
        last = rnd.choice(LAST)
        if (first, last) not in used_names:
            used_names.add((first, last))
            break
    email = f"{LATIN[first]}.u{uid}@reserve.test"
    phone = "09" + rnd.choice(["12", "13", "19", "35", "36", "37", "38", "39", "15", "17"]) + f"{rnd.randrange(10**7):07d}"
    return (uid, f"{first} {last}", email, phone, role, created)


HOST_IDS, GUEST_IDS = [], []
uid = 16
# Hotel groups / operators are hosts too
HOTEL_HOSTS = [(16, "گروه هتل‌های پارس‌گشت", "parsgasht.hotels@reserve.test"),
               (17, "شرکت گردشگری خلیج فارس", "khalijfars.tourism@reserve.test"),
               (18, "مجموعه اقامتی میراث", "miras.lodges@reserve.test")]
for hid, name, email in HOTEL_HOSTS:
    users.append((hid, name, email, f"0912{5550000 + hid:07d}", "host", datetime(2025, 3, 10 + hid - 16, 10, 0)))
    HOST_IDS.append(hid)
uid = 19
for _ in range(9):  # individual hosts
    users.append(new_person(uid, "host", datetime(2025, rnd.randint(4, 12), rnd.randint(1, 28), rnd.randint(8, 22))))
    HOST_IDS.append(uid)
    uid += 1
for _ in range(36):  # guests
    created = datetime(2025, 9, 1) + timedelta(days=rnd.randint(0, 420), minutes=rnd.randint(0, 1440))
    users.append(new_person(uid, "guest", created))
    GUEST_IDS.append(uid)
    uid += 1
ALL_GUESTS = GUEST_IDS + [8, 9, 10, 11, 12, 13, 14, 15]
INDIV_HOSTS = HOST_IDS[3:] + [2, 3, 4, 5, 6, 7]

# ----------------------------------------------------------------------------- listings
TYPE_ID = {"villa": 1, "villa_lux": 1, "suite": 2, "apartment": 3, "cabin": 4, "ecolodge": 5, "hotel5": 6,
           "hotel4": 6, "hotel3": 6, "hotel_apartment": 7, "rural": 8, "traditional": 9}

# Well-known hotels (name, city, kind)
HOTELS = [
    ("هتل اسپیناس پالاس", "tehran", "hotel5"), ("هتل پارسیان آزادی", "tehran", "hotel5"),
    ("هتل پارسیان استقلال", "tehran", "hotel5"), ("هتل بین‌المللی لاله", "tehran", "hotel5"),
    ("هتل هما تهران", "tehran", "hotel5"), ("هتل فردوسی تهران", "tehran", "hotel4"),
    ("هتل عباسی", "isfahan", "hotel5"), ("هتل کوثر اصفهان", "isfahan", "hotel5"),
    ("هتل پیروزی اصفهان", "isfahan", "hotel4"), ("هتل عالی‌قاپو", "isfahan", "hotel4"),
    ("هتل سنتی ملک‌التجار اصفهان", "isfahan", "traditional"), ("اقامتگاه سنتی خانه بخردی", "isfahan", "traditional"),
    ("هتل سنتی باغ مشیرالممالک", "yazd", "traditional"), ("هتل سنتی داد", "yazd", "traditional"),
    ("هتل سنتی لب‌خندق", "yazd", "traditional"), ("هتل صفاییه یزد", "yazd", "hotel5"),
    ("اقامتگاه سنتی ملک‌التجار یزد", "yazd", "traditional"),
    ("اقامتگاه سنتی خانه منوچهری", "kashan", "traditional"), ("هتل سنتی خانه احسان", "kashan", "traditional"),
    ("هتل سنتی سرای عامری‌ها", "kashan", "traditional"),
    ("هتل بزرگ شیراز", "shiraz", "hotel5"), ("هتل چمران شیراز", "shiraz", "hotel5"),
    ("هتل زندیه", "shiraz", "hotel5"), ("هتل هما شیراز", "shiraz", "hotel5"), ("هتل پارک سعدی", "shiraz", "hotel4"),
    ("هتل درویشی", "mashhad", "hotel5"), ("هتل قصر طلایی", "mashhad", "hotel5"),
    ("هتل پارس مشهد", "mashhad", "hotel5"), ("هتل مدینة‌الرضا", "mashhad", "hotel5"),
    ("هتل هما مشهد", "mashhad", "hotel5"), ("هتل اترک مشهد", "mashhad", "hotel4"),
    ("هتل داریوش کیش", "kish", "hotel5"), ("هتل ترنج کیش", "kish", "hotel5"),
    ("هتل مارینا پارک کیش", "kish", "hotel5"), ("هتل شایان کیش", "kish", "hotel5"),
    ("هتل پارمیس کیش", "kish", "hotel4"), ("هتل آرامش کیش", "kish", "hotel4"),
    ("هتل پارس ائل‌گلی", "tabriz", "hotel5"), ("هتل شهریار تبریز", "tabriz", "hotel5"),
    ("هتل بزرگ رامسر", "ramsar", "hotel4"), ("هتل کادوس رشت", "rasht", "hotel4"),
    ("هتل پارس کرمان", "kerman", "hotel5"), ("هتل اخوان کرمان", "kerman", "hotel3"),
    ("هتل بوعلی همدان", "hamadan", "hotel4"), ("هتل باباطاهر همدان", "hamadan", "hotel3"),
    ("هتل پارسیان کرمانشاه", "kermanshah", "hotel4"), ("هتل لاله سرعین", "sareyn", "hotel4"),
    ("هتل لیپار چابهار", "chabahar", "hotel4"), ("هتل بزرگ زنجان", "zanjan", "hotel4"),
    ("هتل البرز قزوین", "qazvin", "hotel4"), ("هتل هما بندرعباس", "bandarabbas", "hotel5"),
    ("هتل دلوار بوشهر", "bushehr", "hotel4"), ("هتل جزیره قشم", "qeshm", "hotel4"),
    ("هتل سنتی خانه‌های زندیه شیراز", "shiraz", "traditional"), ("هتل سنتی ارگ تبریز", "tabriz", "traditional"),
]

# Generic listings per city: (city, kind, count)
GENERIC = [
    ("ramsar", "villa", 3), ("ramsar", "villa_lux", 1), ("ramsar", "suite", 1),
    ("nowshahr", "villa", 3), ("nowshahr", "villa_lux", 2), ("nowshahr", "apartment", 1),
    ("kelardasht", "villa", 2), ("kelardasht", "cabin", 3),
    ("chalus", "villa", 3), ("chalus", "villa_lux", 1), ("chalus", "cabin", 1),
    ("rasht", "apartment", 2), ("rasht", "suite", 1), ("rasht", "rural", 1),
    ("lahijan", "villa", 2), ("lahijan", "rural", 1),
    ("anzali", "villa", 1), ("anzali", "apartment", 1),
    ("masuleh", "rural", 2), ("masuleh", "cabin", 1),
    ("filband", "cabin", 3), ("filband", "rural", 1),
    ("gorgan", "cabin", 1), ("gorgan", "ecolodge", 1), ("gorgan", "apartment", 1),
    ("lavasan", "villa_lux", 3), ("lavasan", "villa", 1),
    ("shahmirzad", "villa", 2), ("shahmirzad", "rural", 1),
    ("tehran", "apartment", 5), ("tehran", "suite", 3),
    ("isfahan", "apartment", 2), ("isfahan", "suite", 1), ("isfahan", "ecolodge", 1),
    ("shiraz", "apartment", 2), ("shiraz", "ecolodge", 2),
    ("yazd", "ecolodge", 2), ("kashan", "ecolodge", 2), ("abyaneh", "rural", 1),
    ("khur", "ecolodge", 3), ("meybod", "ecolodge", 2),
    ("mashhad", "suite", 3), ("mashhad", "apartment", 2),
    ("tabriz", "apartment", 2), ("kandovan", "ecolodge", 2), ("kandovan", "rural", 1),
    ("kish", "hotel_apartment", 3), ("kish", "villa_lux", 1), ("kish", "suite", 1),
    ("qeshm", "ecolodge", 3), ("qeshm", "villa", 1), ("hormuz", "ecolodge", 3),
    ("bandarabbas", "apartment", 1), ("chabahar", "ecolodge", 1), ("bushehr", "ecolodge", 1),
    ("sareyn", "villa", 2), ("sareyn", "suite", 1), ("sareyn", "cabin", 1),
    ("hamadan", "apartment", 1), ("kerman", "ecolodge", 2), ("kermanshah", "ecolodge", 1),
    ("qazvin", "ecolodge", 1), ("zanjan", "apartment", 1), ("sanandaj", "ecolodge", 1),
    ("sanandaj", "rural", 1), ("khorramabad", "ecolodge", 1), ("shushtar", "traditional", 2),
    ("urmia", "apartment", 1), ("urmia", "villa", 1), ("marivan", "cabin", 1), ("marivan", "rural", 1),
    ("yazd", "traditional", 2), ("kashan", "traditional", 2), ("isfahan", "traditional", 1), ("shiraz", "traditional", 1),
    ("tehran", "apartment", 2), ("nowshahr", "villa", 1), ("kish", "hotel_apartment", 1), ("qeshm", "ecolodge", 1),
]

ADJ_VILLA = ["دوبلکس", "نوساز", "باغ‌دار", "دنج", "مدرن", "حیاط‌دار", "ساحلی", "جنگلی", "ویودار"]
ADJ_ECO = ["کاهگلی", "خشتی", "سنتی", "خانوادگی", "آرام", "باغ‌دار"]
ECO_NAMES = ["نارنج", "گلستان", "خورشید", "ستاره", "مهتاب", "انار", "سرو", "یاس", "بهار", "آفتاب", "نخل", "پونه",
             "بابونه", "سپیدار", "کوثر", "آسمان", "شقایق", "ماه‌منیر", "بی‌بی", "عمارت آقا", "سرای نیاکان"]
NEIGHBORHOODS = {
    "tehran": ["سعادت‌آباد", "ونک", "جردن", "پاسداران", "زعفرانیه", "شهرک غرب", "یوسف‌آباد", "نیاوران"],
    "isfahan": ["جلفا", "چهارباغ بالا", "مرداویج"], "shiraz": ["معالی‌آباد", "قصردشت", "ارم"],
    "mashhad": ["امام رضا", "طبرسی", "خیابان دانشگاه", "سناباد"], "tabriz": ["ولیعصر", "ائل‌گلی", "آبرسان"],
    "rasht": ["گلسار", "منظریه"], "bandarabbas": ["گلشهر"], "hamadan": ["میدان امام"],
    "zanjan": ["خیابان سعدی"], "urmia": ["خیابان والفجر"], "anzali": ["غازیان"], "nowshahr": ["خیابان ساحل"],
    "gorgan": ["ناهارخوران"],
}


def jitter(v: float) -> float:
    return round(v + rnd.uniform(-0.03, 0.03), 6)


def money(lo: float, hi: float) -> int:
    """Random price in millions of toman, rounded to 50,000."""
    return int(round(rnd.uniform(lo, hi) * 1_000_000 / 50_000) * 50_000)


TIER = {"tehran": 1.35, "kish": 1.25, "lavasan": 1.4, "isfahan": 1.05, "shiraz": 1.05, "mashhad": 1.0}


def build_units(kind: str, city_key: str) -> list[tuple]:
    t = TIER.get(city_key, 0.85)
    if kind == "hotel5":
        return [("اتاق دوتخته دبل", 2, 1, 1, 1, money(7.5 * t, 12 * t)),
                ("اتاق توئین", 2, 1, 2, 1, money(7.5 * t, 12 * t)),
                ("سوئیت جونیور", 3, 1, 2, 1, money(12 * t, 18 * t)),
                ("سوئیت رویال", 4, 2, 3, 2, money(22 * t, 35 * t))]
    if kind == "hotel4":
        return [("اتاق یک‌تخته", 1, 1, 1, 1, money(3.5 * t, 5 * t)),
                ("اتاق دوتخته", 2, 1, 1, 1, money(4.5 * t, 7 * t)),
                ("اتاق سه‌تخته", 3, 1, 3, 1, money(6 * t, 8.5 * t))]
    if kind == "hotel3":
        return [("اتاق دوتخته", 2, 1, 1, 1, money(2.5 * t, 3.8 * t)),
                ("اتاق خانوادگی", 4, 1, 3, 1, money(3.8 * t, 5.5 * t))]
    if kind == "traditional":
        rooms = [("اتاق شاه‌نشین", 2, 1, 1, 1, money(4, 7)), ("اتاق ارسی", 2, 1, 1, 1, money(3.5, 6)),
                 ("اتاق پنج‌دری", 4, 1, 3, 1, money(5, 8.5)), ("سوئیت حوض‌خانه", 3, 1, 2, 1, money(5.5, 9))]
        return rnd.sample(rooms, 3)
    if kind == "ecolodge":
        rooms = [("اتاق دونفره", 2, 1, 0, 1, money(1.3, 2.4)), ("اتاق خانوادگی", 5, 1, 0, 1, money(2.2, 3.6)),
                 ("اتاق سه‌نفره", 3, 1, 0, 1, money(1.7, 2.9)), ("کومه سنتی", 2, 1, 1, 1, money(1.5, 2.6))]
        return rnd.sample(rooms, rnd.choice([2, 3]))
    if kind == "rural":
        return [("خانه کامل", rnd.choice([4, 5, 6]), 2, rnd.randint(2, 4), 1, money(1.6, 3.6))]
    if kind == "villa":
        beds = rnd.choice([2, 3, 3, 4])
        return [("ویلا کامل", beds * 2 + rnd.choice([0, 2]), beds, beds + 1, rnd.choice([1, 2]),
                 money(3.8 * t / 0.85 * 0.9, 9 * t / 0.85 * 0.9))]
    if kind == "villa_lux":
        beds = rnd.choice([3, 4, 5])
        return [("ویلا کامل", beds * 2 + 2, beds, beds + 2, rnd.choice([2, 3]), money(11 * t, 24 * t))]
    if kind == "cabin":
        return [("کلبه کامل", rnd.choice([2, 4, 4, 6]), 1, rnd.choice([1, 2, 3]), 1, money(2.4, 5.8))]
    if kind == "hotel_apartment":
        return [("واحد یک‌خوابه", 3, 1, 2, 1, money(5, 8)), ("واحد دوخوابه", 5, 2, 3, 2, money(7.5, 11.5))]
    if kind == "apartment":
        beds = rnd.choice([1, 2, 2, 3])
        return [("آپارتمان کامل", beds * 2 + 1, beds, beds + 1, 1 + (beds == 3), money(2.4 * t, 5.5 * t))]
    return [("سوئیت کامل", rnd.choice([2, 3, 4]), 1, rnd.choice([1, 2]), 1, money(1.8 * t, 3.8 * t))]


def amenities_for(kind: str, region: str) -> list[int]:
    a = {1}
    if kind.startswith("hotel"):
        a |= {2, 7, 9, 10, 15, 16, 18, 19}
        if kind == "hotel5":
            a |= {3, 4, 5} if rnd.random() < 0.8 else {5}
            a |= {20} if region in ("island", "metro", "south") else set()
        if region in ("island", "south"):
            a |= {13}
    elif kind == "traditional":
        a |= {7, 8, 12, 15, 16, 19}
    elif kind in ("ecolodge", "rural"):
        a |= {8, 12, 15} if rnd.random() < 0.7 else {8, 12}
        a |= {6, 10} if kind == "rural" else set()
        if region in ("forest", "north", "village"):
            a |= {14}
    elif kind in ("villa", "villa_lux"):
        a |= {2, 6, 8, 9, 10, 11, 12, 16}
        if kind == "villa_lux" or rnd.random() < 0.35:
            a |= {3}
        if kind == "villa_lux":
            a |= {4, 5, 17, 7}
        if region == "north":
            a |= {13} if rnd.random() < 0.5 else {14}
        if region in ("forest", "mountain"):
            a |= {14}
        if region == "island":
            a |= {13, 7}
    elif kind == "cabin":
        a |= {8, 10, 11, 14, 2}
    elif kind == "hotel_apartment":
        a |= {2, 3, 6, 7, 9, 10, 13, 18, 19, 20}
    else:  # apartment / suite
        a |= {6, 7, 8, 9, 10, 16} | ({2, 18, 17} if rnd.random() < 0.6 else set())
    return sorted(a)


def describe(kind: str, title: str, city_key: str) -> tuple[str, str]:
    c = CITY[city_key]
    sights = SIGHTS[city_key]
    s1, s2 = rnd.sample(sights, 2) if len(sights) > 1 else (sights[0], sights[0])
    minutes = rnd.choice([5, 7, 10, 12, 15, 20])
    hood = rnd.choice(NEIGHBORHOODS.get(city_key, ["مرکز شهر"]))
    if kind == "hotel5":
        d = (f"{title} یکی از هتل‌های پنج‌ستاره {c['name']} است با لابی مجلل، رستوران‌های ایرانی و بین‌المللی، "
             f"استخر و مرکز سلامت. فاصله تا {s1} حدود {minutes} دقیقه با خودرو است و {s2} نیز در نزدیکی هتل قرار دارد. "
             f"صبحانه بوفه و اینترنت پرسرعت رایگان است.")
        addr = f"{c['province']}، {c['name']}، بلوار اصلی، جنب {s1}"
    elif kind in ("hotel4", "hotel3"):
        d = (f"هتلی تمیز و خوش‌موقعیت در {c['name']} با پرسنل خوش‌برخورد و صبحانه ایرانی. "
             f"دسترسی آسان به {s1} و {s2}؛ مناسب سفرهای خانوادگی و کاری.")
        addr = f"{c['province']}، {c['name']}، خیابان {rnd.choice(['امام', 'آزادی', 'ولیعصر', 'شریعتی', 'مطهری'])}"
    elif kind == "traditional":
        d = (f"خانه‌ای تاریخی با حیاط مرکزی، حوض فیروزه‌ای و ارسی‌های رنگی که به اقامتگاه سنتی تبدیل شده است. "
             f"تا {s1} {minutes} دقیقه پیاده راه است. صبحانه سنتی و چای در حیاط، تجربه‌ای اصیل از معماری ایرانی است.")
        addr = f"{c['province']}، {c['name']}، بافت تاریخی، نزدیک {s1}"
    elif kind == "ecolodge":
        d = (f"اقامتگاه بوم‌گردی با اتاق‌های {rnd.choice(ADJ_ECO)} و غذای محلی دست‌پخت خانواده میزبان. "
             f"برنامه‌های گردشگری به {s1} و {s2} با هماهنگی میزبان انجام می‌شود. "
             f"آسمان شب، سکوت و مهمان‌نوازی محلی، ویژگی اصلی این اقامتگاه است.")
        addr = f"{c['province']}، {c['name']}، محله قدیمی، کوچه {rnd.choice(ECO_NAMES)}"
    elif kind == "rural":
        d = (f"خانه روستایی اصیل با ایوان و حیاط، مناسب خانواده‌هایی که آرامش و طبیعت می‌خواهند. "
             f"{s1} در فاصله کوتاهی قرار دارد. نان محلی و لبنیات تازه به سفارش مهمان تهیه می‌شود.")
        addr = f"{c['province']}، {c['name']}، بافت روستایی"
    elif kind in ("villa", "villa_lux"):
        extra = "استخر سرپوشیده آب‌گرم، جکوزی و سونا دارد و " if kind == "villa_lux" else ""
        d = (f"ویلای {rnd.choice(ADJ_VILLA)} در {c['name']} که {extra}برای اقامت خانوادگی کاملاً تجهیز شده است. "
             f"حیاط با آلاچیق و باربیکیو، پارکینگ اختصاصی و فاصله {minutes} دقیقه‌ای تا {s1}. "
             f"برگزاری مهمانی و پخش موسیقی با صدای بلند مجاز نیست.")
        addr = f"{c['province']}، {c['name']}، {rnd.choice(['شهرک', 'جاده', 'بلوار'])} {rnd.choice(ECO_NAMES)}"
    elif kind == "cabin":
        d = (f"کلبه چوبی دنج در دل طبیعت {c['name']} با بخاری هیزمی و بالکن رو به منظره. "
             f"مناسب زوج‌ها و خانواده‌های کوچک؛ تا {s1} {minutes} دقیقه راه است.")
        addr = f"{c['province']}، {c['name']}، جاده جنگلی، کلبه‌های {rnd.choice(ECO_NAMES)}"
    elif kind == "hotel_apartment":
        d = (f"هتل‌آپارتمان با واحدهای مبله و آشپزخانه مجهز، نزدیک {s1}. "
             f"ترانسفر فرودگاه و استخر برای مهمانان رایگان است.")
        addr = f"{c['province']}، {c['name']}، نزدیک {s1}"
    else:
        d = (f"{'آپارتمان' if kind == 'apartment' else 'سوئیت'} مبله و تمیز در محله {hood} {c['name']} "
             f"با دسترسی سریع به {s1} و حمل‌ونقل عمومی. مناسب سفرهای کاری، درمانی و خانوادگی.")
        addr = f"{c['province']}، {c['name']}، {hood}"
    return d, addr


def generic_title(kind: str, city_key: str) -> str:
    c = CITY[city_key]["name"]
    hood = rnd.choice(NEIGHBORHOODS.get(city_key, [c]))
    if kind == "villa":
        return f"ویلا {rnd.choice(ADJ_VILLA)} {rnd.choice(['دوخوابه', 'سه‌خوابه', 'چهارخوابه'])} در {c}"
    if kind == "villa_lux":
        return f"ویلا لوکس استخردار {rnd.choice(['سرپوشیده', 'روباز', 'با جکوزی'])} در {c}"
    if kind == "cabin":
        return f"کلبه چوبی {rnd.choice(['جنگلی', 'کوهستانی', 'رو به دره', 'دنج'])} در {c}"
    if kind == "ecolodge":
        return f"اقامتگاه بوم‌گردی {rnd.choice(ECO_NAMES)} {c}"
    if kind == "rural":
        return f"خانه روستایی {rnd.choice(ECO_NAMES)} در {c}"
    if kind == "hotel_apartment":
        return f"هتل‌آپارتمان {rnd.choice(['ساحل', 'مرجان', 'صدف', 'نیلوفر', 'آبی'])} {c}"
    if kind == "traditional":
        return f"هتل سنتی خانه {rnd.choice(ECO_NAMES)} {c}"
    if kind == "apartment":
        return f"آپارتمان مبله {rnd.choice(['یک‌خوابه', 'دوخوابه', 'سه‌خوابه'])} در {hood}"
    return f"سوئیت {rnd.choice(['دنج', 'مبله', 'نوساز', 'خانوادگی'])} در {hood} {c}"


def host_for(kind: str) -> int:
    if kind in ("hotel5", "hotel4", "hotel3"):
        return rnd.choice(HOST_IDS[:2])
    if kind in ("traditional", "ecolodge"):
        return rnd.choice([18, 18] + INDIV_HOSTS)
    return rnd.choice(INDIV_HOSTS)


listings = [(name, city, kind) for name, city, kind in HOTELS]
for city, kind, count in GENERIC:
    for _ in range(count):
        listings.append((None, city, kind))
rnd.shuffle(listings)

TARGET = 200 - 17
listings = listings[:TARGET]
used_titles = set()

properties, units, photos, prop_amenities = [], [], [], []
pid, unit_id = 18, 26
for name, city_key, kind in listings:
    c = CITY[city_key]
    title = name or generic_title(kind, city_key)
    while title in used_titles:
        title = generic_title(kind, city_key)
    used_titles.add(title)
    desc, addr = describe(kind, title, city_key)
    policy = {"hotel5": 2, "hotel4": 1, "hotel3": 1, "villa_lux": 3, "villa": rnd.choice([2, 3])}.get(kind, rnd.choice([1, 2]))
    check_in = "14:00" if kind.startswith("hotel") or kind == "traditional" else rnd.choice(["14:00", "15:00"])
    check_out = "12:00" if kind != "ecolodge" else rnd.choice(["11:00", "12:00"])
    status = "active"
    properties.append((pid, host_for(kind), c["id"], TYPE_ID[kind], policy, title, desc, addr, jitter(c["lat"]),
                       jitter(c["lon"]), check_in, check_out, status, kind, city_key))
    for i, url in enumerate(photos_for(kind, city_key), start=1):
        photos.append((pid, url, i))
    for a in amenities_for(kind, c["region"]):
        prop_amenities.append((pid, a))
    for u in build_units(kind, city_key):
        units.append((unit_id, pid) + u)
        unit_id += 1
    pid += 1

# A few listings are not public yet / suspended, so the admin panel has something to manage
for idx in (7, 51, 133):
    properties[idx] = properties[idx][:12] + ("draft",) + properties[idx][13:]
properties[95] = properties[95][:12] + ("suspended",) + properties[95][13:]

# Better photos for the 17 original listings (their seed.sql photos are random placeholders)
ORIGINAL_KINDS = {1: ("villa_lux", "nowshahr"), 2: ("villa", "kelardasht"), 3: ("suite", "ramsar"),
                  4: ("traditional", "kashan"), 5: ("rural", "abyaneh"), 6: ("traditional", "yazd"),
                  7: ("ecolodge", "khur"), 8: ("apartment", "tehran"), 9: ("suite", "tehran"),
                  10: ("traditional", "shiraz"), 11: ("hotel_apartment", "kish"), 12: ("villa", "qeshm"),
                  13: ("cabin", "masuleh"), 14: ("suite", "mashhad"), 15: ("apartment", "isfahan"),
                  16: ("traditional", "tabriz"), 17: ("villa", "anzali")}
original_photos = []
for opid, (kind, city_key) in ORIGINAL_KINDS.items():
    for i, url in enumerate(photos_for(kind, city_key), start=1):
        original_photos.append((opid, url, i))

# ----------------------------------------------------------------------------- bookings & reviews
TODAY = date(2026, 11, 9)
REVIEWS = {
    5: ["عالی بود! تمیزی و برخورد میزبان بی‌نظیر بود. حتماً دوباره می‌آییم.",
        "از هر نظر راضی بودیم؛ موقعیت عالی و امکانات کامل مطابق عکس‌ها.",
        "یکی از بهترین اقامت‌های ما بود. صبحانه فوق‌العاده و پرسنل بسیار مؤدب.",
        "فضا خیلی آرام و دلنشین بود، دقیقاً همان چیزی که برای استراحت لازم داشتیم.",
        "همه چیز تمیز و مرتب بود و میزبان قبل از رسیدن هماهنگی کامل انجام داد.",
        "منظره فوق‌العاده‌ای داشت و بچه‌ها خیلی لذت بردند."],
    4: ["در کل خوب بود، فقط وای‌فای کمی ضعیف بود.", "موقعیت عالی و تمیز، ولی پارکینگ کمی کوچک بود.",
        "نسبت به قیمت ارزش خرید خوبی داشت. صبحانه می‌توانست متنوع‌تر باشد.",
        "اتاق تمیز و راحت بود؛ صدای خیابان شب‌ها کمی شنیده می‌شد.",
        "میزبان مهربان و پاسخگو بود. حمام کمی قدیمی بود ولی تمیز."],
    3: ["معمولی بود؛ عکس‌ها کمی بهتر از واقعیت بودند.", "تحویل کلید با تأخیر انجام شد ولی بعدش مشکلی نبود.",
        "برای یک شب خوب است ولی برای اقامت طولانی پیشنهاد نمی‌کنم."],
    2: ["تمیزی مطلوب نبود و آب گرم مشکل داشت."],
}
METHODS = ["zarinpal", "behpardakht_mellat", "sep_saman", "wallet"]
PREFIX = {"zarinpal": "ZP", "behpardakht_mellat": "BP", "sep_saman": "SEP", "wallet": "WL"}
bookings, payments, reviews, favorites = [], [], [], set()
bid = 15
ref_counter = 900000
unit_busy: dict[int, list[tuple[date, date]]] = {}


def free(uid_: int, a: date, b: date) -> bool:
    return all(b <= s or a >= e for s, e in unit_busy.get(uid_, []))


def new_ref(method: str) -> str:
    global ref_counter
    ref_counter += 1
    return f"{PREFIX[method]}-X{ref_counter:09d}"


units_by_prop: dict[int, list[tuple]] = {}
for u in units:
    units_by_prop.setdefault(u[1], []).append(u)

for prop in properties:
    if prop[12] != "active":
        continue
    p_id, kind = prop[0], prop[13]
    popular = kind in ("hotel5", "traditional", "villa_lux", "ecolodge")
    n_past = rnd.randint(1, 6) + (2 if popular else 0)
    n_future = rnd.choice([0, 0, 1, 1, 2])
    plan = [("past", None)] * n_past + [("future", None)] * n_future + ([("cancel", None)] if rnd.random() < 0.15 else [])
    for when, _ in plan:
        unit = rnd.choice(units_by_prop[p_id])
        u_id, max_g = unit[0], unit[3]
        for _attempt in range(10):
            nights = rnd.choice([1, 2, 2, 3, 3, 4, 5])
            if when == "past":
                ci = date(2026, 1, 5) + timedelta(days=rnd.randint(0, 295))
                if ci + timedelta(days=nights) > TODAY - timedelta(days=2):
                    continue
            elif when == "future":
                ci = TODAY + timedelta(days=rnd.randint(4, 120))
            else:
                ci = TODAY + timedelta(days=rnd.randint(-40, 60))
            co = ci + timedelta(days=nights)
            if when == "cancel" or free(u_id, ci, co):
                break
        else:
            continue
        guest = rnd.choice(ALL_GUESTS)
        guests_count = rnd.randint(1, max_g)
        created = datetime.combine(ci - timedelta(days=rnd.randint(3, 35)), datetime.min.time()) + timedelta(
            minutes=rnd.randint(8 * 60, 23 * 60))
        if created.date() >= TODAY:
            created = datetime.combine(TODAY - timedelta(days=1), datetime.min.time()) + timedelta(hours=11)
        method = rnd.choice(METHODS)
        paid_at = created + timedelta(minutes=rnd.randint(1, 6))
        if when == "past":
            status = "completed"
        elif when == "future":
            status = "confirmed" if rnd.random() < 0.85 else "pending"
        else:
            status = "cancelled"
        if status in ("completed", "confirmed", "pending"):
            unit_busy.setdefault(u_id, []).append((ci, co))
        bookings.append((bid, guest, u_id, ci, co, guests_count, status, created))
        if status != "pending":
            payments.append((bid, method, "paid", new_ref(method), paid_at))
        if status == "cancelled":
            payments.append((bid, method, "refunded", new_ref(method), paid_at + timedelta(days=rnd.randint(1, 10))))
        if status == "completed" and rnd.random() < 0.75:
            rating = rnd.choices([5, 4, 3, 2], weights=[52, 33, 12, 3])[0]
            reviews.append((bid, rating, rnd.choice(REVIEWS[rating]),
                            datetime.combine(co, datetime.min.time()) + timedelta(hours=rnd.randint(9, 22))))
        if rnd.random() < 0.18:
            favorites.add((guest, p_id))
        bid += 1


# ----------------------------------------------------------------------------- SQL
def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return f"'{v:%Y-%m-%d %H:%M}+03:30'"
    if isinstance(v, date):
        return f"'{v:%Y-%m-%d}'"
    return "'" + str(v).replace("'", "''") + "'"


def values(rows) -> str:
    return ",\n".join(" (" + ", ".join(q(v) for v in r) + ")" for r in rows)


out = ["-- =====================================================================",
       "-- Extra sample data (generated by scripts/gen_seed_extra.py — do not edit by hand)",
       f"-- {len(properties)} more properties (200 in total), {len(units)} units, {len(bookings)} bookings",
       "-- =====================================================================", "", "BEGIN;", ""]
out += ["INSERT INTO city (id, name, province, country) VALUES",
        values([(CITY[k]["id"], CITY[k]["name"], CITY[k]["province"], "ایران") for k, *_ in NEW_CITIES]) + ";", ""]
out += ["INSERT INTO app_user (id, full_name, email, phone, password_hash, role, created_at) VALUES",
        ",\n".join(f" ({u[0]}, {q(u[1])}, {q(u[2])}, {q(u[3])}, crypt('Pass@1234', gen_salt('bf', 6)), {q(u[4])}, {q(u[5])})"
                   for u in users) + ";", ""]
out += ["INSERT INTO property (id, host_id, city_id, type_id, policy_id, title, description, address, latitude, "
        "longitude, check_in_time, check_out_time, status) VALUES", values([p[:13] for p in properties]) + ";", ""]
out += ["INSERT INTO unit (id, property_id, name, max_guests, bedrooms, beds, bathrooms, base_price_per_night) VALUES",
        values(units) + ";", ""]
out += ["-- Same pricing rules as seed.sql for the new units",
        "INSERT INTO unit_price_calendar (unit_id, day, price, is_available)",
        "SELECT u.id, d::date, round(u.base_price_per_night * CASE",
        "    WHEN d::date BETWEEN '2027-03-19' AND '2027-03-31' THEN 1.60",
        "    WHEN d::date = '2026-12-21' THEN 1.30",
        "    WHEN extract(isodow FROM d) IN (4, 5) THEN 1.25 ELSE 1.00 END / 10000) * 10000, TRUE",
        "FROM unit u CROSS JOIN generate_series('2026-11-01'::date, '2027-03-31'::date, interval '1 day') AS d",
        "WHERE u.id >= 26;", ""]
out += ["INSERT INTO property_amenity (property_id, amenity_id) VALUES", values(prop_amenities) + ";", ""]
out += ["-- Relevant photos for the original 17 listings replace the placeholder ones",
        "DELETE FROM photo WHERE property_id <= 17;",
        "INSERT INTO photo (property_id, unit_id, url, sort_order) VALUES",
        ",\n".join(f" ({p}, NULL, {q(u)}, {o})" for p, u, o in original_photos + photos) + ";", ""]
out += ["INSERT INTO booking (id, guest_id, unit_id, coupon_id, check_in, check_out, guests_count, total_price, status, created_at) VALUES",
        ",\n".join(f" ({b[0]}, {b[1]}, {b[2]}, NULL, {q(b[3])}, {q(b[4])}, {b[5]}, 0, {q(b[6])}, {q(b[7])})"
                   for b in bookings) + ";", "",
        "UPDATE booking b SET total_price = (",
        "    SELECT sum(coalesce(c.price, u.base_price_per_night))",
        "      FROM generate_series(b.check_in, b.check_out - 1, interval '1 day') AS d",
        "      JOIN unit u ON u.id = b.unit_id",
        "      LEFT JOIN unit_price_calendar c ON c.unit_id = b.unit_id AND c.day = d::date)",
        "WHERE b.id >= 15;", ""]
out += ["INSERT INTO payment (booking_id, amount, method, status, transaction_ref, paid_at)",
        "SELECT x.booking_id, CASE WHEN x.status = 'refunded' THEN round(b.total_price * 0.7) ELSE b.total_price END,",
        "       x.method, x.status, x.ref, x.paid_at::timestamptz",
        "FROM (VALUES", values(payments), ") AS x(booking_id, method, status, ref, paid_at)",
        "JOIN booking b ON b.id = x.booking_id;", ""]
out += ["INSERT INTO review (booking_id, rating, comment, created_at) VALUES", values(reviews) + ";", ""]
out += ["INSERT INTO favorite (user_id, property_id) VALUES", values(sorted(favorites)) + "", "ON CONFLICT DO NOTHING;", ""]
out += [f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), (SELECT max(id) FROM {t}));"
        for t in ("app_user", "city", "property", "unit", "booking")]
out += ["", "COMMIT;", ""]
(ROOT / "db" / "seed_extra.sql").write_text("\n".join(out), encoding="utf-8", newline="\n")
print(f"properties={len(properties)} units={len(units)} photos={len(photos) + len(original_photos)} "
      f"bookings={len(bookings)} reviews={len(reviews)} users={len(users)} local_topics={len(LOCAL)}")
