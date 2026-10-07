# Preflight Validation Report

**Run ID:** `19a1b4b29b7c`  
**Generated:** 2026-10-06T12:10:56.078761+00:00  

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
| Total checks | 5 |
| Passed | 5 |
| Failed | 0 |
| Warnings | 0 |

> Preflight validation successful. YAML and SeaTunnel configuration are consistent.

## Problems

### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB-hr_employees`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_employees → sink_public_employees (query: SELECT * FROM src_public_employees).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

