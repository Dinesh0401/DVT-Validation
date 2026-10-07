# Preflight Validation Report

**Run ID:** `54906a8fd21c`  
**Generated:** 2026-10-06T10:48:41.592254+00:00  

## Overall Result

❌ **FAILED**

## Input Files

| File | Path |
|------|------|
| Validation YAML | `contract.yaml` |
| SeaTunnel .conf | `job.conf` |

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 7 |
| Passed | 0 |
| Failed | 3 |
| Warnings | 4 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_SCN`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'AMOUNT' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_SCN.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `AMOUNT`  

#### 2. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_SCN`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'TX_ID' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_SCN.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `TX_ID`  

#### 3. MISSING_SCN_IN_SEATUNNEL

**Job:** `JOB_SCN`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract requires snapshot (SCN) but SeaTunnel source query does not contain 'AS OF SCN'.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_SCN.snapshot`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `AS OF SCN binding`  
**Actual:** `not found`  


### ⚠️ Warnings

#### 1. MISSING_ENGINE

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not specify an engine name.  

**File A:** `contract.yaml`  
**Path A:** `engine.name`  


#### 2. MISSING_CONVENTION

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not have a 'convention' section.  

**File A:** `contract.yaml`  
**Path A:** `convention`  


#### 3. MISSING_ACQUISITION

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not specify an acquisition mode.  

**File A:** `contract.yaml`  
**Path A:** `acquisition`  


#### 4. SNAPSHOT_NOT_BOUND

**Job:** `JOB_SCN`  
**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Job 'JOB_SCN' does not bind the snapshot variable despite snapshot acquisition mode.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_SCN.env.snapshot`  

