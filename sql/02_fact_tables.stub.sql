-- 事实表登记（stub）：仅声明表名与关键字段，供血缘校验与新人理解数据来源。
-- 真实项目中这些表由数仓建模产出，这里只保留字典口径需要的最小结构。

CREATE TABLE f_orders (
    order_id        BIGINT      NOT NULL PRIMARY KEY,
    user_id         BIGINT      NOT NULL,
    session_id      BIGINT      NULL,
    pay_amount      DECIMAL(18, 2) NOT NULL,
    cost_amount     DECIMAL(18, 2) NOT NULL,
    discount_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    commission_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    refund_amount   DECIMAL(18, 2) NOT NULL DEFAULT 0,
    pay_status      VARCHAR(16) NOT NULL,
    refund_status   VARCHAR(16) NOT NULL,
    paid_at         DATETIME    NULL
);

CREATE TABLE f_user_events (
    event_id   BIGINT   NOT NULL PRIMARY KEY,
    user_id    BIGINT   NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    event_at   DATETIME NOT NULL
);

CREATE TABLE f_sessions (
    session_id BIGINT   NOT NULL PRIMARY KEY,
    user_id    BIGINT   NULL,
    started_at DATETIME NOT NULL
);

CREATE TABLE f_inventory_snapshot (
    snapshot_date DATE          NOT NULL,
    sku_id        BIGINT        NOT NULL,
    stock_amount  DECIMAL(18, 2) NOT NULL,
    PRIMARY KEY (snapshot_date, sku_id)
);

CREATE TABLE f_sku_stock (
    sku_id       BIGINT NOT NULL PRIMARY KEY,
    on_hand_qty  INT    NOT NULL,
    in_sale      TINYINT NOT NULL DEFAULT 1
);

CREATE TABLE f_delivery (
    delivery_id  BIGINT   NOT NULL PRIMARY KEY,
    order_id     BIGINT   NOT NULL,
    promised_at  DATETIME NOT NULL,
    delivered_at DATETIME NULL
);

CREATE TABLE f_job_run (
    job_id      BIGINT   NOT NULL PRIMARY KEY,
    job_name    VARCHAR(128) NOT NULL,
    sla_at      DATETIME NOT NULL,
    finished_at DATETIME NULL
);
