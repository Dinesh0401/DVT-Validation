# Preflight Validation Report

**Run ID:** `a307028dc875`  
**Generated:** 2026-10-06T10:41:12.662068+00:00  

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

**Job:** `JOB-hr_employees`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** Source SQL has minor dialect differences (whitespace, alias style) between contract and SeaTunnel. Columns and source table match.  

**File A:** `duckdb.yaml`  
**Path A:** `job.JOB-hr_employees.source.projection`  
**File B:** `seatunnel.conf`  
**Path B:** `source.Jdbc.query`  


#### 2. TRANSFORM_CHAIN_INFO

**Job:** `JOB-hr_employees`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_public_employees → sink_public_employees (query: SELECT * FROM src_public_employees).  

**File B:** `seatunnel.conf`  
**Path B:** `transform.SQL`  

