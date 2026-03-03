# Revit (RVT) Support Guide

## Overview
Revit files (.rvt) are proprietary BIM files. There are multiple approaches to extract data.

## Option 1: Manual IFC Export (Recommended for Now)
1. Open RVT file in Revit
2. File → Export → IFC
3. Process IFC file with Serapeum's IFC processor

**Pros**: No API needed, works offline  
**Cons**: Manual step required

## Option 2: Autodesk Forge API (Future)
Forge API can programmatically extract data from RVT files.

### Prerequisites
- Autodesk Forge account
- API credentials (Client ID + Secret)
- `forge-sdk` Python library

### Implementation Outline
```python
from forge import ForgeClient

client = ForgeClient(client_id=xxx, client_secret=xxx)

# Upload RVT
urn = client.upload_file("model.rvt")

# Extract properties
properties = client.get_model_properties(urn)

# Download as IFC
ifc_urn = client.translate_to_ifc(urn)
```

### Cost
- Forge API has free tier (50 translations/month)
- Production use may require paid plan

## Option 3: Revit API (Advanced)
Requires Revit installed and running a Revit addin.

## Recommendation
1. **Now**: Use manual IFC export
2. **Future**: Implement Forge API integration for automation

## Status
✅ IFC processor ready (handles exported IFC)
⚠️ RVT direct support requires Forge API or manual export
📝 Pathway defined for future implementation
