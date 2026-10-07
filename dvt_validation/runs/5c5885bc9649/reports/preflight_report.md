# Preflight Validation Report

**Run ID:** `5c5885bc9649`  
**Generated:** 2026-10-07T13:03:25.997457+00:00  

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

**Job:** `JOB-banking_accounts`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_accounts → sink_public_accounts (query: SELECT * FROM src_public_accounts).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

