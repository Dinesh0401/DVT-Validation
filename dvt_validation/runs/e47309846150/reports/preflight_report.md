# Preflight Validation Report

**Run ID:** `e47309846150`  
**Generated:** 2026-10-06T10:40:57.822752+00:00  

## Overall Result

✅ **SUCCESS**

## Input Files

| File | Path |
|------|------|
| Validation YAML | `duckdb.yaml` |
| SeaTunnel .conf | `seatunnel.conf` |

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 2 |
| Passed | 2 |
| Failed | 0 |
| Warnings | 0 |

> Preflight validation successful. YAML and SeaTunnel configuration are consistent.

## Problems

### ℹ️ Information

#### 1. SQL_DIALECT_DIFFERENCE

**Job:** `JOB-admin_orders`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** Source SQL has minor dialect differences (whitespace, alias style) between contract and SeaTunnel. Columns and source table match.  

**File A:** `duckdb.yaml`  
**Path A:** `job.JOB-admin_orders.source.projection`  
**File B:** `seatunnel.conf`  
**Path B:** `source.Jdbc.query`  


#### 2. TRANSFORM_CHAIN_INFO

**Job:** `JOB-admin_orders`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_orders → sink_public_orders (query: SELECT * FROM src_public_orders).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

