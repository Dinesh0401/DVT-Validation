# Preflight Validation Report

**Run ID:** `e55187777f40`  
**Generated:** 2026-10-07T15:58:38.482105+00:00  

## Overall Result

❌ **REVIEW**

## Input Files

| File | Path |
|------|------|
| Validation YAML | `contract.yaml` |
| SeaTunnel .conf | `job.conf` |

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 3 |
| Passed | 1 |
| Failed | 0 |
| Warnings | 2 |

> Preflight validation completed with warnings requiring review before migration.

## Problems

### ⚠️ Warnings

#### 1. MISSING_CONVENTION

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not have a 'convention' section.  

**File A:** `contract.yaml`  
**Path A:** `convention`  


#### 2. MISSING_ACQUISITION

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not specify an acquisition mode.  

**File A:** `contract.yaml`  
**Path A:** `acquisition`  


### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB_TEST_GATE`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_cust → sink_cust (query: SELECT ID AS id, NAME AS name FROM src_cust).  

**File B:** `job.conf`  
**Path B:** `transform.SQL`  

