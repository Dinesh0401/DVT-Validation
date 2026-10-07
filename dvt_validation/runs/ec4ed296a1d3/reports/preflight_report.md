# Preflight Validation Report

**Run ID:** `ec4ed296a1d3`  
**Generated:** 2026-10-06T10:48:41.491969+00:00  

## Overall Result

✅ **SUCCESS**

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
| Failed | 0 |
| Warnings | 3 |

> Preflight validation successful. YAML and SeaTunnel configuration are consistent.

## Problems

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


### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB_001`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_dept → sink_dept (query: SELECT DEPT_ID AS dept_id, DEPT_NAME AS dept_name, MANAGER_ID AS manager_id FROM src_dept).  

**File B:** `job.conf`  
**Path B:** `transform.SQL`  

