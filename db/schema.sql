-- =====================================================================
-- Schema for the accommodation booking site (based on ERD.md)
-- PostgreSQL 14+
-- Amounts are in toman (numeric(14,0)); times are Asia/Tehran
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- for the exclusion constraint that prevents overlapping bookings
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- for bcrypt hashing of passwords in the seed

DROP TABLE IF EXISTS message, favorite, review, payment, booking, coupon,
    photo, property_amenity, amenity, unit_price_calendar, unit, property,
    cancellation_policy, property_type, city, app_user CASCADE;

-- ---------------------------------------------------------------- USER
-- "user" is a reserved word in PostgreSQL, so the table is named app_user
CREATE TABLE app_user (
    id            SERIAL PRIMARY KEY,
    full_name     VARCHAR(120) NOT NULL,
    email         VARCHAR(160) NOT NULL UNIQUE,
    phone         VARCHAR(11)  NOT NULL UNIQUE CHECK (phone ~ '^09[0-9]{9}$'),
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(10)  NOT NULL DEFAULT 'guest' CHECK (role IN ('guest', 'host', 'admin')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- CITY
CREATE TABLE city (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(80) NOT NULL,
    province VARCHAR(80) NOT NULL,
    country  VARCHAR(80) NOT NULL DEFAULT 'ایران',
    UNIQUE (name, province)
);

-- ------------------------------------------------------- PROPERTY_TYPE
CREATE TABLE property_type (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE
);

-- ------------------------------------------------- CANCELLATION_POLICY
CREATE TABLE cancellation_policy (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(60)  NOT NULL UNIQUE,
    free_cancel_days INT          NOT NULL CHECK (free_cancel_days >= 0),
    refund_percent   NUMERIC(5,2) NOT NULL CHECK (refund_percent BETWEEN 0 AND 100)
);

-- ------------------------------------------------------------ PROPERTY
CREATE TABLE property (
    id             SERIAL PRIMARY KEY,
    host_id        INT NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
    city_id        INT NOT NULL REFERENCES city(id) ON DELETE RESTRICT,
    type_id        INT NOT NULL REFERENCES property_type(id) ON DELETE RESTRICT,
    policy_id      INT NOT NULL REFERENCES cancellation_policy(id) ON DELETE RESTRICT,
    title          VARCHAR(200) NOT NULL,
    description    TEXT,
    address        VARCHAR(300) NOT NULL,
    latitude       NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude      NUMERIC(9,6) CHECK (longitude BETWEEN -180 AND 180),
    check_in_time  TIME NOT NULL DEFAULT '14:00',
    check_out_time TIME NOT NULL DEFAULT '12:00',
    status         VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'suspended'))
);
CREATE INDEX ix_property_city   ON property(city_id);
CREATE INDEX ix_property_host   ON property(host_id);
CREATE INDEX ix_property_status ON property(status);

-- ---------------------------------------------------------------- UNIT
CREATE TABLE unit (
    id                   SERIAL PRIMARY KEY,
    property_id          INT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    name                 VARCHAR(120) NOT NULL,
    max_guests           INT NOT NULL CHECK (max_guests > 0),
    bedrooms             INT NOT NULL DEFAULT 0 CHECK (bedrooms >= 0),
    beds                 INT NOT NULL DEFAULT 1 CHECK (beds >= 0),
    bathrooms            INT NOT NULL DEFAULT 1 CHECK (bathrooms >= 0),
    base_price_per_night NUMERIC(14,0) NOT NULL CHECK (base_price_per_night > 0)
);
CREATE INDEX ix_unit_property ON unit(property_id);

-- ------------------------------------------------- UNIT_PRICE_CALENDAR
CREATE TABLE unit_price_calendar (
    id           SERIAL PRIMARY KEY,
    unit_id      INT NOT NULL REFERENCES unit(id) ON DELETE CASCADE,
    day          DATE NOT NULL,
    price        NUMERIC(14,0) NOT NULL CHECK (price > 0),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (unit_id, day)   -- one price per unit per day
);

-- ------------------------------------------------------------- AMENITY
CREATE TABLE amenity (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    icon VARCHAR(60)
);

CREATE TABLE property_amenity (
    property_id INT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    amenity_id  INT NOT NULL REFERENCES amenity(id) ON DELETE CASCADE,
    PRIMARY KEY (property_id, amenity_id)
);

-- --------------------------------------------------------------- PHOTO
CREATE TABLE photo (
    id          SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    unit_id     INT REFERENCES unit(id) ON DELETE CASCADE,
    url         VARCHAR(500) NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0
);
CREATE INDEX ix_photo_property ON photo(property_id);

-- -------------------------------------------------------------- COUPON
CREATE TABLE coupon (
    id               SERIAL PRIMARY KEY,
    code             VARCHAR(40)  NOT NULL UNIQUE,
    discount_percent NUMERIC(5,2) NOT NULL CHECK (discount_percent > 0 AND discount_percent <= 100),
    valid_from       DATE NOT NULL,
    valid_to         DATE NOT NULL,
    usage_limit      INT  NOT NULL CHECK (usage_limit > 0),
    CHECK (valid_to >= valid_from)
);

-- ------------------------------------------------------------- BOOKING
CREATE TABLE booking (
    id           SERIAL PRIMARY KEY,
    guest_id     INT NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
    unit_id      INT NOT NULL REFERENCES unit(id) ON DELETE RESTRICT,
    coupon_id    INT REFERENCES coupon(id) ON DELETE SET NULL,
    check_in     DATE NOT NULL,
    check_out    DATE NOT NULL,
    guests_count INT  NOT NULL CHECK (guests_count > 0),
    total_price  NUMERIC(14,0) NOT NULL CHECK (total_price >= 0),
    status       VARCHAR(10) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (check_out > check_in),
    -- Prevent overlapping bookings: two active bookings on the same unit must not share a night
    CONSTRAINT booking_no_overlap EXCLUDE USING gist (
        unit_id WITH =,
        daterange(check_in, check_out, '[)') WITH &&
    ) WHERE (status IN ('pending', 'confirmed'))
);
CREATE INDEX ix_booking_guest ON booking(guest_id);
CREATE INDEX ix_booking_unit  ON booking(unit_id);

-- ------------------------------------------------------------- PAYMENT
CREATE TABLE payment (
    id              SERIAL PRIMARY KEY,
    booking_id      INT NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    amount          NUMERIC(14,0) NOT NULL CHECK (amount >= 0),
    method          VARCHAR(30) NOT NULL,
    status          VARCHAR(10) NOT NULL CHECK (status IN ('paid', 'failed', 'refunded')),
    transaction_ref VARCHAR(64) UNIQUE,
    paid_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_payment_booking ON payment(booking_id);

-- -------------------------------------------------------------- REVIEW
CREATE TABLE review (
    id         SERIAL PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE REFERENCES booking(id) ON DELETE CASCADE,
    rating     INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------ FAVORITE
CREATE TABLE favorite (
    user_id     INT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    property_id INT NOT NULL REFERENCES property(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, property_id)
);

-- ------------------------------------------------------------- MESSAGE
CREATE TABLE message (
    id          SERIAL PRIMARY KEY,
    sender_id   INT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    receiver_id INT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    booking_id  INT REFERENCES booking(id) ON DELETE SET NULL,
    body        TEXT NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (sender_id <> receiver_id)
);
CREATE INDEX ix_message_pair ON message(sender_id, receiver_id);
