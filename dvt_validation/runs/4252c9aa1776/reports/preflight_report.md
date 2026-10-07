# Preflight Validation Report

**Run ID:** `4252c9aa1776`  
**Generated:** 2026-10-06T11:35:51.404403+00:00  

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
| Passed | 0 |
| Failed | 2 |
| Warnings | 2 |

> Preflight validation failed. Fix the reported mismatches before migration.

## Problems

### ❌ Errors

#### 1. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_TEST_GATE`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'ID' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_TEST_GATE.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `ID`  

#### 2. MISSING_COLUMN_IN_SEATUNNEL

**Job:** `JOB_TEST_GATE`  
**Stage:** cross_validation  
**Severity:** ERROR  

**Problem:** Contract column 'NAME' is missing from SeaTunnel source projection.  

**File A:** `contract.yaml`  
**Path A:** `job.JOB_TEST_GATE.source.columns`  
**File B:** `job.conf`  
**Path B:** `source.query`  

**Expected:** `NAME`  

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

