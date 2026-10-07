-- ============================================================================
-- PostgreSQL Matching Demo Target Schema & Data Script
-- Database: migration_exercise
-- Schema: public
-- Tables: customers, products, orders, order_items, payments, inventory
-- ============================================================================

-- 1. Clean existing tables if re-running
DROP TABLE IF EXISTS public.payments CASCADE;
DROP TABLE IF EXISTS public.order_items CASCADE;
DROP TABLE IF EXISTS public.orders CASCADE;
DROP TABLE IF EXISTS public.inventory CASCADE;
DROP TABLE IF EXISTS public.products CASCADE;
DROP TABLE IF EXISTS public.customers CASCADE;

-- 2. Create Target Tables (in lowercase matching the contract target)
CREATE TABLE public.customers (
    customer_id   BIGINT PRIMARY KEY,
    first_name    VARCHAR(50),
    last_name     VARCHAR(50),
    email         VARCHAR(100),
    phone         VARCHAR(30),
    address       VARCHAR(200),
    city          VARCHAR(50),
    state         VARCHAR(50),
    postal_code   VARCHAR(20),
    created_at    TIMESTAMP
);

CREATE TABLE public.products (
    product_id    BIGINT PRIMARY KEY,
    product_name  VARCHAR(100),
    category_id   BIGINT,
    brand         VARCHAR(50),
    price         NUMERIC(10, 2),
    description   VARCHAR(255),
    size          VARCHAR(20),
    color         VARCHAR(30),
    active        INT,
    created_at    TIMESTAMP
);

CREATE TABLE public.orders (
    order_id         BIGINT PRIMARY KEY,
    customer_id      BIGINT REFERENCES public.customers(customer_id),
    order_date       TIMESTAMP,
    total_amount     NUMERIC(10, 2),
    status           VARCHAR(30),
    shipping_address VARCHAR(200)
);

CREATE TABLE public.order_items (
    order_item_id  BIGINT PRIMARY KEY,
    order_id       BIGINT REFERENCES public.orders(order_id),
    product_id     BIGINT REFERENCES public.products(product_id),
    quantity       INT,
    unit_price     NUMERIC(10, 2),
    discount       NUMERIC(10, 2) DEFAULT 0.00
);

CREATE TABLE public.payments (
    payment_id      BIGINT PRIMARY KEY,
    order_id        BIGINT REFERENCES public.orders(order_id),
    payment_date    TIMESTAMP,
    amount          NUMERIC(10, 2),
    payment_method  VARCHAR(50),
    payment_status  VARCHAR(30),
    transaction_id  VARCHAR(100)
);

CREATE TABLE public.inventory (
    inventory_id   BIGINT PRIMARY KEY,
    product_id     BIGINT REFERENCES public.products(product_id),
    stock_qty      INT,
    reorder_level  INT,
    updated_at     TIMESTAMP
);

-- 3. Insert Matching Demo Data (Mirroring Oracle so DVT passes 100%)
INSERT INTO public.customers (customer_id, first_name, last_name, email, phone, address, city, state, postal_code, created_at) VALUES
(1, 'John', 'Doe', 'john.doe@example.com', '+1-555-0101', '100 Main St', 'New York', 'NY', '10001', '2026-01-10 10:00:00'),
(2, 'Jane', 'Smith', 'jane.smith@example.com', '+1-555-0102', '200 Oak Ave', 'Los Angeles', 'CA', '90001', '2026-01-12 11:30:00'),
(3, 'Michael', 'Johnson', 'michael.j@example.com', '+1-555-0103', '300 Pine Rd', 'Chicago', 'IL', '60601', '2026-02-01 09:15:00'),
(4, 'Emily', 'Davis', 'emily.d@example.com', '+1-555-0104', '400 Elm St', 'Houston', 'TX', '77001', '2026-02-15 14:45:00'),
(5, 'David', 'Brown', 'david.b@example.com', '+1-555-0105', '500 Maple Dr', 'Miami', 'FL', '33101', '2026-03-01 16:20:00');

INSERT INTO public.products (product_id, product_name, category_id, brand, price, description, size, color, active, created_at) VALUES
(101, 'Running Pro Shoes', 1, 'Nike', 120.00, 'Breathable road running shoes', '10', 'Black/Red', 1, '2026-01-05 08:00:00'),
(102, 'Soccer Match Ball', 2, 'Adidas', 45.50, 'FIFA certified training soccer ball', '5', 'White/Blue', 1, '2026-01-05 08:30:00'),
(103, 'Performance Dri-FIT Shirt', 3, 'Under Armour', 35.00, 'Moisture-wicking athletic tee', 'L', 'Navy', 1, '2026-01-06 10:00:00'),
(104, 'Basketball Grip Elite', 2, 'Wilson', 60.00, 'Indoor composite leather basketball', '7', 'Orange', 1, '2026-01-07 11:00:00'),
(105, 'Fitness Water Bottle 1L', 4, 'HydroFlask', 25.00, 'Insulated stainless steel sports bottle', '1L', 'Silver', 1, '2026-01-08 12:00:00');

INSERT INTO public.orders (order_id, customer_id, order_date, total_amount, status, shipping_address) VALUES
(1001, 1, '2026-02-10 14:00:00', 165.50, 'COMPLETED', '100 Main St, New York, NY 10001'),
(1002, 2, '2026-02-12 15:30:00', 120.00, 'COMPLETED', '200 Oak Ave, Los Angeles, CA 90001'),
(1003, 3, '2026-02-14 11:15:00', 70.00, 'PROCESSING', '300 Pine Rd, Chicago, IL 60601'),
(1004, 4, '2026-02-18 16:45:00', 60.00, 'COMPLETED', '400 Elm St, Houston, TX 77001'),
(1005, 5, '2026-02-20 10:20:00', 145.00, 'SHIPPED', '500 Maple Dr, Miami, FL 33101');

INSERT INTO public.order_items (order_item_id, order_id, product_id, quantity, unit_price, discount) VALUES
(5001, 1001, 101, 1, 120.00, 0.00),
(5002, 1001, 102, 1, 45.50, 0.00),
(5003, 1002, 101, 1, 120.00, 0.00),
(5004, 1003, 103, 2, 35.00, 0.00),
(5005, 1004, 104, 1, 60.00, 0.00),
(5006, 1005, 101, 1, 120.00, 0.00),
(5007, 1005, 105, 1, 25.00, 0.00);

INSERT INTO public.payments (payment_id, order_id, payment_date, amount, payment_method, payment_status, transaction_id) VALUES
(9001, 1001, '2026-02-10 14:05:00', 165.50, 'CREDIT_CARD', 'SUCCESS', 'TXN-98127391'),
(9002, 1002, '2026-02-12 15:35:00', 120.00, 'PAYPAL', 'SUCCESS', 'TXN-98127392'),
(9003, 1003, '2026-02-14 11:20:00', 70.00, 'DEBIT_CARD', 'PENDING', 'TXN-98127393'),
(9004, 1004, '2026-02-18 16:50:00', 60.00, 'CREDIT_CARD', 'SUCCESS', 'TXN-98127394'),
(9005, 1005, '2026-02-20 10:25:00', 145.00, 'APPLE_PAY', 'SUCCESS', 'TXN-98127395');

INSERT INTO public.inventory (inventory_id, product_id, stock_qty, reorder_level, updated_at) VALUES
(701, 101, 50, 10, '2026-03-01 08:00:00'),
(702, 102, 85, 15, '2026-03-01 08:00:00'),
(703, 103, 120, 25, '2026-03-01 08:00:00'),
(704, 104, 40, 10, '2026-03-01 08:00:00'),
(705, 105, 200, 30, '2026-03-01 08:00:00');
