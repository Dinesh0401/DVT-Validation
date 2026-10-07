# Preflight Validation Report

**Run ID:** `cd2fa1fc9fbc`  
**Generated:** 2026-10-07T12:59:51.961957+00:00  

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
| Total checks | 4 |
| Passed | 1 |
| Failed | 1 |
| Warnings | 2 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_PAYROLL`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'TAX_DEDUCTION' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_PAYROLL.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `TAX_DEDUCTION`  

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

**Job:** `JOB_PAYROLL`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_sal → sink_sal (query: SELECT EMP_ID, SALARY, BONUS FROM src_sal).  

**File B:** `job.conf`  
**Path B:** `transform.SQL`  

