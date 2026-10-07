# Preflight Validation Report

**Run ID:** `c2fbe2a86354`  
**Generated:** 2026-10-06T11:22:53.133301+00:00  

## Overall Result

❌ **BLOCKED**

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
| Failed | 1 |
| Warnings | 1 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. MISSING_SCN_IN_SEATUNNEL

**Job:** `JOB_001`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract requires snapshot (SCN) but SeaTunnel source query does not contain 'AS OF SCN'.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_001.snapshot`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `AS OF SCN binding`  
**Actual:** `not found`  


### ⚠️ Warnings

#### 1. SNAPSHOT_NOT_BOUND

**Job:** `JOB_001`  
**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Job 'JOB_001' does not bind the snapshot variable despite snapshot acquisition mode.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_001.env.snapshot`  


### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB_001`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_dept → sink_dept (query: SELECT DEPT_ID AS dept_id, DEPT_NAME AS dept_name, MANAGER_ID AS manager_id FROM src_dept).  

**File B:** `job.conf`  
**Path B:** `transform.SQL`  

