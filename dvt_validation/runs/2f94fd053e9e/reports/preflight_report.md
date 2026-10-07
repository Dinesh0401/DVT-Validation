# Preflight Validation Report

**Run ID:** `2f94fd053e9e`  
**Generated:** 2026-10-06T10:43:10.636748+00:00  

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
| Total checks | 6 |
| Passed | 0 |
| Failed | 6 |
| Warnings | 0 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. MISSING_SOURCE

**Job:** `ST:source`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'source' has no source block.  

**File A:** `job.conf`  
**Path A:** `job.source.source`  


#### 2. MISSING_SINK

**Job:** `ST:source`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'source' has no sink JDBC block.  

**File A:** `job.conf`  
**Path A:** `job.source.sink`  


#### 3. MISSING_SOURCE

**Job:** `ST:transform`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'transform' has no source block.  

**File A:** `job.conf`  
**Path A:** `job.transform.source`  


#### 4. MISSING_SINK

**Job:** `ST:transform`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'transform' has no sink JDBC block.  

**File A:** `job.conf`  
**Path A:** `job.transform.sink`  


#### 5. MISSING_SOURCE

**Job:** `ST:sink`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'sink' has no source block.  

**File A:** `job.conf`  
**Path A:** `job.sink.source`  


#### 6. MISSING_SINK

**Job:** `ST:sink`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'sink' has no sink JDBC block.  

**File A:** `job.conf`  
**Path A:** `job.sink.sink`  

