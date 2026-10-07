# Preflight Validation Report

**Run ID:** `010444b0988b`  
**Generated:** 2026-10-06T12:10:36.127445+00:00  

## Overall Result

❌ **READY**

## Input Files

| File | Path |
|------|------|
| Validation YAML | `duckdb.yaml` |
| SeaTunnel .conf | `seatunnel.conf` |

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 6 |
| Passed | 6 |
| Failed | 0 |
| Warnings | 0 |

> Preflight validation successful. YAML and SeaTunnel configuration are consistent.

## Problems

### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_customers`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_customers → sink_public_customers (query: SELECT * FROM src_public_customers).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  


#### 2. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_inventory`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_inventory → sink_public_inventory (query: SELECT * FROM src_public_inventory).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  


#### 3. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_order_items`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_order_items → sink_public_order_items (query: SELECT * FROM src_public_order_items).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  


#### 4. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_orders`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_orders → sink_public_orders (query: SELECT * FROM src_public_orders).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  


#### 5. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_payments`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_payments → sink_public_payments (query: SELECT * FROM src_public_payments).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  


#### 6. TRANSFORM_CHAIN_INFO

**Job:** `JOB-sports_products`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_products → sink_public_products (query: SELECT * FROM src_public_products).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

