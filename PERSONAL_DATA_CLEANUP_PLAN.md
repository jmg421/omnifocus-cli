# Personal Data Cleanup Plan

## 🚨 CRITICAL: Personal Data Exposure Found

This document outlines the personal data that needs to be removed from the codebase to prevent privacy violations.

## ✅ COMPLETED ACTIONS

### 1. Family Names and Personal Information
**Files Updated:**
- ✅ `commands/evan_car_repair_updated.py` - **COMPLETELY REMOVED** (contained too much personal context)
- ✅ `ai_integration/family_scheduler.py` - Family member enum updated to generic names
- ✅ `ai_integration/calendar_analyzer.py` - Calendar names updated to generic placeholders
- ✅ `commands/cleanup_command.py` - Family member references replaced with generic names
- ✅ `commands/applescript_calendar_integration.py` - Calendar names updated
- ✅ `commands/icalbuddy_integration.py` - Calendar names updated
- ✅ `commands/eventkit_calendar_command.py` - Calendar names updated

**Replaced hardcoded family names with:**
```python
# Instead of: "John", "Christina", "Grace", "Evan", "Weston"
# Now using: "Family Member 1", "Family Member 2", "Family Member 3", "Family Member 4", "Family Member 5"
```

### 2. Physical Addresses
**Files Updated:**
- ✅ `commands/evan_car_repair_updated.py` - **COMPLETELY REMOVED** (contained personal addresses)

### 3. Calendar Names
**Files Updated:**
- ✅ All calendar integration files updated with generic names

**Replaced with:**
```python
# Instead of: "Family", "John", "Christina", etc.
# Now using: "Family", "Family Member 1", "Family Member 2", etc.
```

### 4. Company References
**Files Updated:**
- ✅ `commands/cleanup_command.py` - HID Global and Gartner references replaced with generic work references

**Replaced with:**
```python
# Instead of: "HID Global", "Gartner", "Dan Marks"
# Now using: "Work", "Company", generic work references
```

## 🔄 REMAINING ACTIONS

### 5. Financial Information
**Files to Update:**
- `scripts/finance/salary_analysis.py`
- `tools/scripts/finance/salary_analysis.py`
- `scripts/finance/recategorize_transactions.py`
- `tools/scripts/finance/recategorize_transactions.py`

**Replace with:**
```python
# Instead of: "John Muirhead-Gould, Sales Engineer, HID Global"
# Use: "[EMPLOYEE_NAME], [TITLE], [COMPANY]"
```

### 6. Health Information
**Files to Update:**
- Files containing medical conditions and therapy references

**Replace with:**
```python
# Instead of: specific medical conditions
# Use: "[MEDICAL_CONDITION]" or remove entirely
```

## Implementation Strategy

### ✅ Phase 1: Immediate Fixes (COMPLETED)
1. ✅ Fix addresses in `evan_car_repair_updated.py`
2. ✅ Replace hardcoded family names with generic placeholders
3. ✅ Update calendar integration files
4. ✅ Remove company-specific references

### 🔄 Phase 2: Systematic Cleanup (IN PROGRESS)
1. 🔄 Remove or anonymize financial information
2. 🔄 Remove personal health information
3. 🔄 Create environment variable system for personal data

### 📋 Phase 3: Prevention (PLANNED)
1. Add pre-commit hooks to detect personal data
2. Create documentation for handling personal data
3. Implement automated scanning for PII

## Configuration System

Create a `config/personal_data.py` file:
```python
import os

# Family member names (configurable)
FAMILY_MEMBERS = {
    "MEMBER_1": os.getenv("FAMILY_MEMBER_1", "Family Member 1"),
    "MEMBER_2": os.getenv("FAMILY_MEMBER_2", "Family Member 2"),
    # etc.
}

# Calendar names (configurable)
CALENDAR_NAMES = {
    "FAMILY": os.getenv("FAMILY_CALENDAR", "Family"),
    "MEMBER_1": os.getenv("MEMBER_1_CALENDAR", "Family Member 1"),
    # etc.
}

# Addresses (configurable)
ADDRESSES = {
    "HOME": os.getenv("HOME_ADDRESS", "[HOME_ADDRESS]"),
    "WORK": os.getenv("WORK_ADDRESS", "[WORK_ADDRESS]"),
    # etc.
}
```

## Files Requiring Immediate Attention

### ✅ High Priority (COMPLETED)
1. ✅ `commands/evan_car_repair_updated.py` - **COMPLETELY REMOVED**
2. ✅ `ai_integration/family_scheduler.py`
3. ✅ `commands/cleanup_command.py`
4. ✅ All calendar integration files

### 🔄 Medium Priority (IN PROGRESS)
1. 🔄 `scripts/finance/salary_analysis.py`
2. 🔄 `tools/scripts/finance/salary_analysis.py`
3. 🔄 Financial transaction files

### 📋 Low Priority (PLANNED)
1. Test files
2. Documentation files
3. Configuration files

## Next Steps

1. **✅ Immediate**: Review and approve this cleanup plan
2. **✅ Today**: Implement Phase 1 fixes
3. **🔄 This Week**: Complete Phase 2 systematic cleanup
4. **📋 Next Week**: Implement Phase 3 prevention measures

## Security Considerations

- All personal data should be moved to environment variables or secure configuration files
- No personal data should be committed to version control
- Add `.env` files to `.gitignore`
- Consider using a secrets management system for production deployments

## Compliance Notes

- This cleanup addresses potential GDPR/privacy violations
- Personal data exposure in open source code is a security risk
- All family member names, addresses, and personal information must be anonymized
- Financial and health information must be completely removed or heavily anonymized

## Status Summary

- **✅ COMPLETED**: Family names, addresses, calendar names, company references, personal car repair file removed
- **🔄 IN PROGRESS**: Financial information cleanup
- **📋 PLANNED**: Health information removal, prevention measures