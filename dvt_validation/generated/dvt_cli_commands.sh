#!/usr/bin/env bash
# Google Cloud Data Validation Tool (DVT) Execution Script
# Generated dynamically by Stage-1 Preflight Pipeline
# Use --dry-run to print generated SQL without executing data validation

DRY_RUN_FLAG="${1:---dry-run}"
SRC_CONN="oracle_source"
TGT_CONN="postgresql_target"

echo "==================================================="
echo "Running DVT Validations (oracle_source -> postgresql_target) with mode: $DRY_RUN_FLAG"
echo "==================================================="

# --- JOB-shop_audit_event ---
echo "[DVT] Validating Schema: JOB-shop_audit_event (SHOP.AUDIT_EVENT=shop.audit_event)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.AUDIT_EVENT=shop.audit_event $DRY_RUN_FLAG
echo "[DVT] Validating Row Counts: JOB-shop_audit_event"
data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.AUDIT_EVENT=shop.audit_event --primary-keys event_id $DRY_RUN_FLAG

# --- JOB-shop_branch ---
echo "[DVT] Validating Schema: JOB-shop_branch (SHOP.BRANCH=shop.branch)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.BRANCH=shop.branch $DRY_RUN_FLAG
echo "[DVT] Validating Row Counts: JOB-shop_branch"
data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.BRANCH=shop.branch  $DRY_RUN_FLAG

# --- JOB-shop_customer ---
echo "[DVT] Validating Schema: JOB-shop_customer (SHOP.CUSTOMER=shop.client)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.CUSTOMER=shop.client $DRY_RUN_FLAG
echo "[DVT] Validating Row Counts: JOB-shop_customer"
data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.CUSTOMER=shop.client  $DRY_RUN_FLAG

# --- JOB-shop_order_summary ---
echo "[DVT] Validating Schema: JOB-shop_order_summary (SHOP.ORDER_SUMMARY=shop.order_summary)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.ORDER_SUMMARY=shop.order_summary $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_order_summary"

# --- JOB-shop_orders ---
echo "[DVT] Validating Schema: JOB-shop_orders (SHOP.ORDERS=shop.orders)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.ORDERS=shop.orders $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_orders"

# --- JOB-shop_orders_2023--merged ---
echo "[DVT] Validating Schema: JOB-shop_orders_2023--merged (SHOP.ORDERS_2023=shop.orders_history)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.ORDERS_2023=shop.orders_history $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_orders_2023--merged"

# --- JOB-shop_party--company ---
echo "[DVT] Validating Schema: JOB-shop_party--company (SHOP.PARTY=shop.party_company)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PARTY=shop.party_company $DRY_RUN_FLAG
echo "[DVT] Validating Row Counts: JOB-shop_party--company"
data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PARTY=shop.party_company  $DRY_RUN_FLAG

# --- JOB-shop_party--person ---
echo "[DVT] Validating Schema: JOB-shop_party--person (SHOP.PARTY=shop.party_person)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PARTY=shop.party_person $DRY_RUN_FLAG
echo "[DVT] Validating Row Counts: JOB-shop_party--person"
data-validation validate row -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PARTY=shop.party_person  $DRY_RUN_FLAG

# --- JOB-shop_price_history ---
echo "[DVT] Validating Schema: JOB-shop_price_history (SHOP.PRICE_HISTORY=shop.price_history)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PRICE_HISTORY=shop.price_history $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_price_history"

# --- JOB-shop_product ---
echo "[DVT] Validating Schema: JOB-shop_product (SHOP.PRODUCT=shop.product_catalogue)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.PRODUCT=shop.product_catalogue $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_product"

# --- JOB-shop_stock ---
echo "[DVT] Validating Schema: JOB-shop_stock (SHOP.STOCK=shop.stock_by_product)"
data-validation validate schema -sc $SRC_CONN -tc $TGT_CONN -tbls SHOP.STOCK=shop.stock_by_product $DRY_RUN_FLAG
echo "[DVT] Complex Transform: Custom Query Validation recommended for JOB-shop_stock"
