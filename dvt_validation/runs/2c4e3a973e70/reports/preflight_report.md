# Preflight Validation Report

**Run ID:** `2c4e3a973e70`  
**Generated:** 2026-10-06T10:44:01.036414+00:00  

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
| Total checks | 4 |
| Passed | 0 |
| Failed | 4 |
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

**Job:** `ST:sink`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'sink' has no source block.  

**File A:** `job.conf`  
**Path A:** `job.sink.source`  


#### 4. MISSING_SINK

**Job:** `ST:sink`  
**Stage:** conf_validation  
**Severity:** ERROR  

**Problem:** Data job 'sink' has no sink JDBC block.  

**File A:** `job.conf`  
**Path A:** `job.sink.sink`  

