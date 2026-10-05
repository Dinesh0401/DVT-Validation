# Stage-1 Pre-migration Preflight Verification Report (Oracle -> PostgreSQL)

**Execution Timestamp:** 2026-10-05 22:11:19
**Scope:** Pre-migration Contract vs Execution Plan Preflight (Zero DB Access)
**Engines:** Source = `Oracle`, Target = `PostgreSQL`

---

## Executive Summary

| Metric | Count | Status |
| :--- | :--- | :--- |
| **Total Logical Migration Jobs** | 12 | Specification Baseline |
| **Active & Fully Paired Jobs** | 11 | Verified (100% Contract Agreement) |
| **Explicitly Blocked Jobs** | 1 | ⚠️ Hard Blocker (1 job) |
| **Contract Validation Checks** | 106 | 28 Direct SQL / 78 Runtime |
| **Snapshot SCN Binding** | 11/11 Active | Verified Pinned Reads |
| **Semantic Query Parity** | 11 Match, 0 Review | Verified Semantic Equivalence |
| **Target DDL & DML Schema Alignment** | 11/11 Active | 100% Column Alignment |

---

## 1. Multi-Layer Verification Matrix

| Layer | Scope | Checks Performed | Result |
| :--- | :--- | :--- | :--- |
| **Layer 1: Structural Integrity** | YAML & HOCON syntax | Tokenization, brace balancing, job definitions | **PASS** (11 active, 1 blocked) |
| **Layer 2: Relation & Entity Mapping** | Source & Target relations | Oracle schema/table -> PostgreSQL schema/table | **PASS** (11/11 verified) |
| **Layer 3: Snapshot Binding** | Pinned read consistency | Verified snapshot parameter on all table reads | **PASS** (11/11 verified) |
| **Layer 4: Semantic Query Equivalence** | AST & dialect analysis | Functions, types, where-filters, regex, hashes | **PASS (100% Semantic Match)** |
| **Layer 5: Target DDL & Schema Consistency** | PostgreSQL DDL vs DML | Table names, column counts, column orders, types | **PASS** (11/11 exact match) |
| **Layer 6: DVT Execution Readiness** | DVT plan & CLI commands | Schema, Row, Column, Custom-Query coverage | **PASS** (Ready for dry-run) |

---

## 2. Table-by-Table Verification Evidence

| Job ID | Order | Oracle Source | PostgreSQL Target | Primary Key | Snapshot Bound | Query Semantics | DDL Columns | Checks |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **JOB-shop_audit_event** | 1 | `SHOP.AUDIT_EVENT` | `shop.audit_event` | `event_id` | ✅ Bound | ✅ Match | 100% | 11 |
| **JOB-shop_branch** | 2 | `SHOP.BRANCH` | `shop.branch` | `None` | ✅ Bound | ✅ Match | 100% | 8 |
| **JOB-shop_customer** | 3 | `SHOP.CUSTOMER` | `shop.client` | `None` | ✅ Bound | ✅ Match | 100% | 15 |
| **JOB-shop_order_summary** | 4 | `SHOP.ORDER_SUMMARY` | `shop.order_summary` | `None` | ✅ Bound | ✅ Match | 100% | 7 |
| **JOB-shop_orders** | 5 | `SHOP.ORDERS` | `shop.orders` | `None` | ✅ Bound | ✅ Match | 100% | 11 |
| **JOB-shop_orders_2023--merged** | 6 | `SHOP.ORDERS_2023` | `shop.orders_history` | `None` | ✅ Bound | ✅ Match | 100% | 8 |
| **JOB-shop_party--company** | 7 | `SHOP.PARTY` | `shop.party_company` | `None` | ✅ Bound | ✅ Match | 100% | 8 |
| **JOB-shop_party--person** | 8 | `SHOP.PARTY` | `shop.party_person` | `None` | ✅ Bound | ✅ Match | 100% | 8 |
| **JOB-shop_price_history** | 9 | `SHOP.PRICE_HISTORY` | `shop.price_history` | `None` | ✅ Bound | ✅ Match | 100% | 10 |
| **JOB-shop_product** | 10 | `SHOP.PRODUCT` | `shop.product_catalogue` | `None` | ✅ Bound | ✅ Match | 100% | 8 |
| **JOB-shop_stock** | 11 | `SHOP.STOCK` | `shop.stock_by_product` | `product_id` | ✅ Bound | ✅ Match | 100% | 12 |
| **JOB-shop_order_line** | *N/A* | *Blocked in Spec* | *Blocked in Spec* | *N/A* | *N/A* | ⚠️ **BLOCKED** | *None* | 0 |

---

## 3. Dynamic Audit Findings & Dialect Notes

### 3.1 Hard Gate: 1 Blocked Job(s) Identified
- **Job ID:** `JOB-shop_order_line`
  - **Status:** ⚠️ **BLOCKED (Hard Stop)**
  - **Reason:** Explicitly blocked in migration specification (no query emitted by transpiler)
  - **Resolution Requirement:** Before initiating Stage-2 migration execution, the data engineering team must either supply the missing query specification or officially de-scope this entity.

### 3.2 Dialect Semantic Findings & Equivalences (2 jobs)
#### Job: `JOB-shop_customer`
- Fixed-width vs variable-width type semantics: Source query uses CHAR(2) which carries blank-padding semantics (trailing spaces if value < 2 chars in Oracle); contract specifies variable-length VARCHAR/TEXT(2).
- Cryptographic hash function equivalence: Source digest function in Oracle is mathematically equivalent to standard contract hash function.
- Regex extraction equivalence: Source REGEXP_SUBSTR extracts match group, equivalent to contract REGEXP_EXTRACT / LIST_EXTRACT.

#### Job: `JOB-shop_price_history`
- Window ordering semantics: Source query uses ORDER BY ... DESC without explicit NULLS positioning (natively defaults to NULLS FIRST in Oracle, but NULLS LAST in PostgreSQL/DuckDB). Contract explicitly declares NULLS FIRST for cross-engine parity.

---

## 4. DVT Stage-2 Execution Plan

The preflight pipeline has dynamically generated the following execution artifacts in `generated/`:
1. **`dvt_validation_plan.yaml`**: Complete validation specification mapping Oracle source $\to$ PostgreSQL target connections, schemas, tables, primary keys, snapshot bindings, and check coverage.
2. **`dvt_cli_commands.sh` / `dvt_cli_commands.bat`**: Ready-to-run Google Cloud DVT CLI commands supporting `--dry-run` mode.
3. **`dvt_configs/*.yaml`**: Native DVT config files for schema and row validation.
