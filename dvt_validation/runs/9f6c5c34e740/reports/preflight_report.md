# Preflight Validation Report

**Run ID:** `9f6c5c34e740`  
**Generated:** 2026-10-06T11:38:06.697696+00:00  

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
| Total checks | 5 |
| Passed | 0 |
| Failed | 3 |
| Warnings | 2 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. TARGET_TABLE_MISMATCH

**Job:** `JOB_INV`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Target table differs: contract='tbl_inventory_v2', SeaTunnel='wrong_table_name'.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_INV.target`  
**File B:** `job.conf`  
**Path B:** `sink.table`  

**Expected:** `tbl_inventory_v2`  
**Actual:** `wrong_table_name`  


#### 2. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_INV`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'QTY' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_INV.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `QTY`  

#### 3. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_INV`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'SKU' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_INV.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `SKU`  

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

