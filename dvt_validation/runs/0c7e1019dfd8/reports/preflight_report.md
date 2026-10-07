# Preflight Validation Report

**Run ID:** `0c7e1019dfd8`  
**Generated:** 2026-10-06T10:48:00.849508+00:00  

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
| Total checks | 5 |
| Passed | 0 |
| Failed | 1 |
| Warnings | 4 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. UNMATCHED_YAML_JOB

**Job:** `JOB_PAYROLL`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract job 'JOB_PAYROLL' has no matching SeaTunnel job definition.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_PAYROLL`  
**File B:** `job.conf`  


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


#### 4. EXTRA_SEATUNNEL_JOB

**Job:** `ST:default`  
**Stage:** cross_validation  
**Severity:** WARNING  

**Problem:** SeaTunnel job 'ST:default' has no matching contract job.  

**File A:** `job.conf`  
**Path A:** `job.ST:default`  
**File B:** `contract.yaml`  

