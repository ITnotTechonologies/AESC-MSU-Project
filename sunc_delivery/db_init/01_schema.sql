-- =========================================================
--  SUNC Delivery — PostgreSQL schema
--  File: db_init/01_schema.sql
-- =========================================================

BEGIN;

-- =========================================================
-- ENUMS
-- =========================================================

DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('client', 'courier', 'admin');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE order_status AS ENUM (
        'created',
        'pending_courier',
        'accepted',
        'picked_up',
        'delivering',
        'delivered',
        'received',
        'rejected_by_courier',
        'cancelled_by_client',
        'cancelled_by_system'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE product_source AS ENUM ('internal', 'ozon', 'yandex_market');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE message_type AS ENUM ('user', 'system');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE system_event_type AS ENUM (
        'order_created',
        'courier_assigned',
        'courier_accepted',
        'courier_rejected',
        'order_picked_up',
        'order_delivering',
        'order_delivered',
        'order_received',
        'order_cancelled',
        'status_changed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =========================================================
-- USERS
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'client',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =========================================================
-- CATEGORIES
-- =========================================================

CREATE TABLE IF NOT EXISTS categories (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);

-- =========================================================
-- PRODUCTS
-- =========================================================

CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    price           DECIMAL(10, 2) NOT NULL,
    image_url       VARCHAR(500),
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    source_type     product_source NOT NULL DEFAULT 'internal',
    is_available    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_products_price_non_negative CHECK (price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_source_type ON products(source_type);
CREATE INDEX IF NOT EXISTS idx_products_is_available ON products(is_available);

-- =========================================================
-- COURIERS
-- =========================================================

CREATE TABLE IF NOT EXISTS couriers (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_approved     BOOLEAN NOT NULL DEFAULT FALSE,
    rating          DECIMAL(3, 2) NOT NULL DEFAULT 5.00,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_couriers_rating_range CHECK (rating >= 0 AND rating <= 5)
);

CREATE INDEX IF NOT EXISTS idx_couriers_is_approved ON couriers(is_approved);
CREATE INDEX IF NOT EXISTS idx_couriers_user_id ON couriers(user_id);

-- =========================================================
-- ORDERS
-- =========================================================

CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    courier_id      INTEGER REFERENCES couriers(id) ON DELETE SET NULL,
    status          order_status NOT NULL DEFAULT 'created',
    delivery_point  VARCHAR(255) NOT NULL,
    total_price     DECIMAL(10, 2) NOT NULL DEFAULT 0,
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    accepted_at     TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    received_at     TIMESTAMPTZ,

    CONSTRAINT chk_orders_total_price_non_negative CHECK (total_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_courier_id ON orders(courier_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- =========================================================
-- ORDER ITEMS
-- =========================================================

CREATE TABLE IF NOT EXISTS order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL,
    price_snapshot  DECIMAL(10, 2) NOT NULL,
    CONSTRAINT chk_order_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_order_items_price_snapshot_non_negative CHECK (price_snapshot >= 0)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- =========================================================
-- MESSAGES (chat + system notifications)
-- =========================================================

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sender_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    receiver_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    type            message_type NOT NULL DEFAULT 'user',
    system_event    system_event_type,
    text            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at         TIMESTAMPTZ,

    CONSTRAINT chk_messages_system_event_required
        CHECK (type <> 'system' OR system_event IS NOT NULL),

    CONSTRAINT chk_messages_user_sender_required
        CHECK (type <> 'user' OR sender_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_messages_order_id ON messages(order_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_receiver_id ON messages(receiver_id);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);

-- =========================================================
-- ORDER STATUS HISTORY
-- =========================================================

CREATE TABLE IF NOT EXISTS order_status_history (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status      order_status,
    new_status      order_status NOT NULL,
    changed_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id);
CREATE INDEX IF NOT EXISTS idx_order_status_history_created_at ON order_status_history(created_at DESC);

COMMIT;