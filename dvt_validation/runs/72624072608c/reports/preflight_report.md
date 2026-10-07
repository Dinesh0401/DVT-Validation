# Preflight Validation Report

**Run ID:** `72624072608c`  
**Generated:** 2026-10-06T12:01:27.813146+00:00  

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
| Total checks | 1 |
| Passed | 1 |
| Failed | 0 |
| Warnings | 0 |

> Preflight validation successful. YAML and SeaTunnel configuration are consistent.

## Problems

### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB-admin_orders`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_orders → sink_public_orders (query: SELECT * FROM src_public_orders).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

