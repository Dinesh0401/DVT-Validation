# Preflight Validation Report

**Run ID:** `d21586bbe100`  
**Generated:** 2026-10-07T10:18:11.773825+00:00  

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
| Total checks | 2 |
| Passed | 1 |
| Failed | 0 |
| Warnings | 1 |

> Preflight validation completed with warnings requiring review before migration.

## Problems

### ⚠️ Warnings

#### 1. MISSING_ACQUISITION

**Stage:** contract_validation  
**Severity:** WARNING  

**Problem:** Validation contract does not specify an acquisition mode.  

**File A:** `contract.yaml`  
**Path A:** `acquisition`  


### ℹ️ Information

#### 1. TRANSFORM_CHAIN_INFO

**Job:** `JOB_EMPLOYEES_DVT`  
**Stage:** cross_validation  
**Severity:** INFO  

**Problem:** SeaTunnel transform: src_emp → sink_emp (query: SELECT EMP_ID AS emp_id, FIRST_NAME AS first_name, SALARY AS salary FROM src_emp).  

**File B:** `job.conf`  
**Path B:** `transform.SQL`  

