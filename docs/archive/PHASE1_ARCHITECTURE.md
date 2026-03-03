# Phase 1 Fortification: Architecture & Implementation

> **Status**: Complete ✅  
> **Completion Date**: January 2026  
> **Version**: 1.0  
> **Focus**: Data Integrity, Resilience, and Reliable VLM Prompting

## Overview

Phase 1 Fortification addresses critical architectural gaps identified in the initial VLM generic response bug. Rather than a quick fix, we implemented a comprehensive fortification strategy across five core dimensions:

1. **Database Schema Extensions** — Audit trails, conflict tracking, and failure recovery logging
2. **Cross-Modal Data Reconciliation** — Detect and resolve conflicts between OCR, VLM, and spatial layout data
3. **Resilience Framework** — Dead-letter queuing, retry logic, and graceful degradation
4. **Resource Monitoring** — Memory/VRAM awareness with dynamic model selection
5. **Prompt Validation Gates** — Prevent truncation, injection, and malformed instructions

## Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Ingestion                        │
│              (PDF, Images, CAD, BIM, etc.)                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         Data Consolidation Service                           │
│  (Unified context from native OCR + layout metadata)         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Resource Monitor [NEW]                          │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ • Detect available VRAM (psutil, pynvml)             │  │
│   │ • Select model: Qwen2-VL (4.6GB) or Mistral (4GB)    │  │
│   │ • Recommend throttling at 80%+ usage                 │  │
│   └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         Two-Stage Vision Engine                              │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Stage 1: Quick Classification [NEW VALIDATION]      │   │
│  │ • Input: unified_context, document type             │   │
│  │ • Prompt Validator: prevent truncation/injection    │   │
│  │ • LLM: Classify document (specification, drawing, etc) │
│  │ • Output: document_type, confidence                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Stage 2: Specialized Extraction [NEW VALIDATION]    │   │
│  │ • Input: unified_context, document_type, role       │   │
│  │ • Prompt Validator: prevent truncation/injection    │   │
│  │ • LLM: Extract entities (systems, requirements)     │   │
│  │ • Resilience Framework: fallback on failure         │   │
│  │ • Output: extracted_data, confidence                │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│      Cross-Modal Reconciliation [NEW]                        │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ Input: native_ocr, vlm_output, spatial_layout       │  │
│   │                                                      │  │
│   │ • Detect conflicts: type, severity, confidence      │  │
│   │ • Resolve: native > vlm > spatial strategy          │  │
│   │ • Output: reconciled_fields, conflict_trace         │  │
│   │                                                      │  │
│   │ Strategies:                                          │  │
│   │ - NATIVE: Trust OCR when both sources exist         │  │
│   │ - VLM: Use VLM when OCR unavailable                │  │
│   │ - SPATIAL: Use layout-inferred data as fallback     │  │
│   │ - HYBRID: Combine confidence scores                 │  │
│   └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         Resilience Framework [NEW]                           │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ • Dead-letter queue: log failures → failed_extractions│ │
│   │ • Retry loop: auto-retry Stage 2 with backoff       │  │
│   │ • Graceful degradation: fallback to Stage 1 output  │  │
│   │ • Backup storage: store stage2_backup on VLM fail   │  │
│   └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 1 Audit Trail (Database)                  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ • data_conflicts: reconciliation results & strategy  │  │
│   │ • engineer_validations: human corrections & feedback │  │
│   │ • failed_extractions: VLM failures with diagnostics │  │
│   │ • extraction_accuracy: quality metrics per document  │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Database Schema Extensions

**File**: [src/db/migrations/001_phase1_fortification.sql](../src/db/migrations/001_phase1_fortification.sql)

Four new tables enable comprehensive audit trails and failure tracking:

#### `data_conflicts` Table
Tracks reconciliation decisions between OCR, VLM, and spatial layout data.

```sql
CREATE TABLE data_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    conflict_type TEXT NOT NULL,           -- (e.g., "text_content", "bounding_box")
    source1 TEXT,                          -- Field from source 1 (native OCR)
    source2 TEXT,                          -- Field from source 2 (VLM output)
    resolved_value TEXT,                   -- Final reconciled value
    resolution_strategy TEXT,               -- ("native", "vlm", "spatial", "hybrid")
    confidence_score REAL,                 -- 0.0–1.0 confidence in resolution
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(page_id) REFERENCES pages(id),
    CHECK(conflict_type IN ('text_content', 'bounding_box', 'entity_type'))
);
```

**Use Case**: Debug VLM vs. OCR disagreements; analyze conflict patterns over time.

#### `engineer_validations` Table
Collects human corrections and engineer feedback for confidence learning (Phase 2).

```sql
CREATE TABLE engineer_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    field_name TEXT,                       -- (e.g., "equipment_name", "system_type")
    vlm_output TEXT,                       -- VLM's original extraction
    engineer_correction TEXT,               -- Corrected value
    feedback_type TEXT,                    -- ("typo", "partial", "wrong_classification")
    confidence_impact REAL,                -- Predicted confidence adjustment
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
```

**Use Case**: Track engineer corrections to improve prompt engineering and model selection (Phase 2).

#### `failed_extractions` Table
Dead-letter queue for VLM failures with diagnostics for root-cause analysis.

```sql
CREATE TABLE failed_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    error_type TEXT,                       -- ("timeout", "truncated_input", "invalid_json", "unknown")
    error_message TEXT,
    vlm_model TEXT,                        -- Which model failed (for model selection tuning)
    unified_context_length INTEGER,        -- Input length (detect truncation)
    retry_count INTEGER DEFAULT 0,
    last_retry_timestamp DATETIME,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_method TEXT,                -- How failure was resolved
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(page_id) REFERENCES pages(id),
    FOREIGN KEY(document_id) REFERENCES documents(id),
    CHECK(error_type IN ('timeout', 'truncated_input', 'invalid_json', 'unknown'))
);
```

**Use Case**: Diagnose why VLM calls fail; enable data-driven model switching and prompt optimization.

#### `extraction_accuracy` Table
Aggregated quality metrics per document for observability.

```sql
CREATE TABLE extraction_accuracy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    total_pages INTEGER,
    successful_extractions INTEGER,
    failed_extractions INTEGER,
    conflicts_detected INTEGER,
    engineer_corrections INTEGER,
    average_confidence_score REAL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id),
    UNIQUE(document_id)
);
```

**Use Case**: High-level document quality dashboard; track improvement over time.

### 2. Cross-Modal Validator

**File**: [src/core/cross_modal_validator.py](../src/core/cross_modal_validator.py)

Detects and resolves conflicts between OCR, VLM, and spatial layout data using configurable strategies.

#### Key Classes

```python
class ConflictType(Enum):
    TEXT_CONTENT = "text_content"
    BOUNDING_BOX = "bounding_box"
    ENTITY_TYPE = "entity_type"

class ResolutionStrategy(Enum):
    NATIVE = "native"         # Trust OCR when both exist
    VLM = "vlm"               # Use VLM when OCR unavailable
    SPATIAL = "spatial"       # Use layout inference as fallback
    HYBRID = "hybrid"         # Weighted confidence scoring
```

#### Main API

```python
class CrossModalValidator:
    def detect_conflicts(self, ocr_data, vlm_data, layout_data) -> List[ConflictRecord]:
        """
        Compare OCR, VLM, and layout data to identify discrepancies.
        Returns: List of ConflictRecord with type, sources, and confidence.
        """
    
    def resolve_conflict(self, conflict: ConflictRecord, strategy: ResolutionStrategy) -> str:
        """
        Apply resolution strategy to pick the best field value.
        Returns: Reconciled value with confidence score.
        """
    
    def validate_cross_modal_data(self, ocr_data, vlm_data, layout_data) -> ReconciledData:
        """
        Full reconciliation pipeline: detect → resolve → return unified output.
        Returns: ReconciledData with reconciled_fields, conflicts, and resolutions.
        """
    
    def assess_data_quality(self, conflicts: List[ConflictRecord]) -> Dict[str, float]:
        """
        Compute data quality metrics: conflict_ratio, avg_confidence, etc.
        """
```

#### Example Usage

```python
from src.core.cross_modal_validator import CrossModalValidator, ResolutionStrategy

validator = CrossModalValidator()

# Reconcile data from three sources
result = validator.validate_cross_modal_data(
    ocr_data={"equipment_name": "HVAC Unit A-1", "capacity": "10 tons"},
    vlm_data={"equipment_name": "HVAC Unit A1", "capacity": ""},  # VLM typo, missing capacity
    layout_data={"bounding_box": (100, 200, 300, 400)}
)

# result.reconciled_fields:
# {
#     "equipment_name": {"value": "HVAC Unit A-1", "source": "ocr", "confidence": 0.95},
#     "capacity": {"value": "10 tons", "source": "ocr", "confidence": 1.0}
# }

# result.conflicts: list of ConflictRecord for each discrepancy
# result.resolutions: strategy used (NATIVE, VLM, SPATIAL, HYBRID)
```

### 3. Resilience Framework

**File**: [src/core/resilience_framework.py](../src/core/resilience_framework.py)

Handles VLM failures gracefully with dead-letter queuing, retry loops, and fallback strategies.

#### Key Methods

```python
class ResilienceFramework:
    def handle_extraction_failure(self, page_id: int, error: Exception, 
                                   context_length: int, db: DatabaseManager) -> None:
        """
        Log failure to dead-letter queue (failed_extractions table).
        Captures error type, message, model, input length for root-cause analysis.
        """
    
    def retry_pending_failures(self, db: DatabaseManager, max_retries: int = 3, 
                               backoff_factor: float = 2.0) -> Dict[str, Any]:
        """
        Auto-retry failed extractions with exponential backoff.
        Returns: summary of retried pages and new outcomes.
        """
    
    def store_stage2_backup(self, page_id: int, stage1_output: Dict, 
                            db: DatabaseManager) -> None:
        """
        On VLM failure, store Stage 1 output as backup (graceful degradation).
        Enables fallback analysis without re-running Stage 1.
        """
```

#### Retry Strategy

1. **Detect Failure**: VLM call times out, returns invalid JSON, or throws exception.
2. **Log Dead-Letter**: Write to `failed_extractions` table with error details.
3. **Store Backup**: Save Stage 1 output to database for fallback.
4. **Auto-Retry**: Background worker retries with backoff:
   - 1st retry: 2 seconds
   - 2nd retry: 4 seconds
   - 3rd retry: 8 seconds
5. **Graceful Degradation**: If retry fails, use Stage 1 output as final result.

#### Integration with Vision Engine

The `TwoStageVisionEngine` automatically logs failures:

```python
# In process_page_two_stage():
try:
    stage2_result = self.stage2_engine.extract(...)
except Exception as e:
    if self.resilience and self.db:
        self.resilience.handle_extraction_failure(
            page_id=page_id,
            error=e,
            context_length=len(unified_context),
            db=self.db
        )
    # Fallback to Stage 1 output or retry on next run
```

### 4. Resource Monitor

**File**: [src/core/resource_monitor.py](../src/core/resource_monitor.py)

Detects available VRAM and memory, dynamically selects models, and recommends throttling.

#### Key Methods

```python
class ResourceMonitor:
    def get_available_vram(self) -> float:
        """
        Detect NVIDIA GPU VRAM using pynvml.
        Falls back to psutil system memory if no GPU.
        Returns: Available memory in GB.
        """
    
    def select_model_for_resources(self, available_memory: float) -> str:
        """
        Select optimal VLM model based on available memory:
        - >= 6 GB: Qwen2-VL-7B (4.6 GB, best quality)
        - >= 4.5 GB: Mistral-7B (4.0 GB, fast)
        - < 4.5 GB: Use Stage 1 only, skip Stage 2
        Returns: Model name or None if insufficient memory.
        """
    
    def should_throttle(self, current_usage_percent: float, threshold: float = 80.0) -> bool:
        """
        Recommend throttling at 80%+ memory usage to prevent OOM.
        Returns: True if throttling recommended.
        """
    
    def score_resources(self, available_gb: float) -> float:
        """
        Compute resource score (0.0–1.0) based on available memory.
        Used for load balancing and queue management.
        """
```

#### Usage Example

```python
from src.core.resource_monitor import ResourceMonitor

monitor = ResourceMonitor()

# Check available memory
available_vram = monitor.get_available_vram()
print(f"Available VRAM: {available_vram} GB")

# Select model based on resources
model = monitor.select_model_for_resources(available_vram)
print(f"Selected model: {model}")  # e.g., "Qwen2-VL-7B" or "Mistral-7B"

# Check if throttling needed
if monitor.should_throttle(current_usage=95.0):
    print("Memory usage high; reduce batch size or queue size")
```

### 5. Prompt Validator

**File**: [src/core/prompt_validator.py](../src/core/prompt_validator.py)

Prevents prompt truncation, injection attacks, and malformed instructions.

#### Key Methods

```python
class PromptValidator:
    def validate_prompt(self, prompt: str, max_length: int = 8000, 
                        model: str = "qwen") -> Tuple[bool, str]:
        """
        Validate prompt before sending to VLM.
        Checks:
        - Length doesn't exceed model's context window
        - No injection patterns (escaped quotes, shell commands)
        - Well-formed JSON/Python blocks
        Returns: (is_valid, error_message_if_invalid)
        """
    
    def sanitize_user_prompt(self, user_input: str) -> str:
        """
        Clean user input to prevent injection attacks.
        Escapes: quotes, backticks, shell metacharacters.
        Returns: Sanitized prompt.
        """
```

#### Validation Checklist

1. **Length Check**: Prompt + context ≤ model's max tokens (typically 8K).
2. **Injection Prevention**: No escaped quotes, shell commands, or code blocks.
3. **Syntax Check**: Valid JSON/Python if prompt contains code.
4. **Format Check**: Required placeholders present (e.g., `{unified_context}`).

#### Integration with Vision Engine

Both Stage 1 and Stage 2 validate prompts before LLM calls:

```python
# Stage 1:
from src.core.prompt_validator import PromptValidator
validator = PromptValidator()

prompt = f"Classify document:\n{unified_context}"
is_valid, error = validator.validate_prompt(prompt)
if not is_valid:
    # Log error and fallback
    self.logger.warning(f"Prompt validation failed: {error}")
    # Use cached Stage 1 result or skip extraction
else:
    stage1_result = self.stage1_engine.extract(prompt)
```

## Integration Points

### Vision Pipeline Integration

The `TwoStageVisionEngine` [src/vision/adaptive_extraction.py](../src/vision/adaptive_extraction.py) now coordinates all Phase 1 components:

```python
from src.vision.adaptive_extraction import TwoStageVisionEngine
from src.core.prompt_validator import PromptValidator
from src.core.resource_monitor import ResourceMonitor
from src.core.cross_modal_validator import CrossModalValidator
from src.core.resilience_framework import ResilienceFramework

# Initialize with all Phase 1 components
engine = TwoStageVisionEngine(
    db=db,                          # Database connection for audit trails
    resilience=ResilienceFramework(),
    resource_monitor=ResourceMonitor(),
    prompt_validator=PromptValidator()
)

# Process page: automatic validation, reconciliation, resilience
result = engine.process_page_two_stage(
    page_id=page_id,
    unified_context=unified_context,
    document_type="specification",
    role="engineer"
)

# Result includes:
# - stage1: classification result
# - stage2: specialized extraction
# - combined_summary: merged output
# - reconciled: cross-modal reconciliation result
# - conflicts: detected conflicts
# - resolutions: applied strategies
```

### Data Consolidation Integration

The `DataConsolidationService` [src/core/data_consolidation_service.py](../src/core/data_consolidation_service.py) now:

1. Builds `unified_context` from native OCR + layout metadata.
2. Passes to Vision Engine (which validates + reconciles).
3. Stores reconciliation results + conflicts in database.
4. Indexes reconciled data in vector store.

## Testing

### Unit Tests

All Phase 1 components have comprehensive unit test coverage:

| Component | Test File | Tests | Status |
|-----------|-----------|-------|--------|
| Database Schema | `tests/unit/test_database_schema.py` | 11 | ✅ Pass |
| Cross-Modal Validator | `tests/unit/test_cross_modal_validator.py` | 27 | ✅ Pass |
| Resilience Framework | `tests/unit/test_resilience_framework.py` | 4 | ✅ Pass |
| Resource Monitor | `tests/unit/test_resource_monitor.py` | 5 | ✅ Pass |
| Prompt Validator | `tests/unit/test_prompt_validator.py` | 5 | ✅ Pass |

### Integration Tests

End-to-end tests validate the full Phase 1 pipeline:

| Test File | Scenarios | Status |
|-----------|-----------|--------|
| `tests/integration/test_cross_modal_integration.py` | Conflict detection & resolution | ✅ Pass |
| `tests/integration/test_phase1_pipeline.py` | Success & failure paths with resilience | ✅ Pass |

**Run All Tests**:
```bash
python -m pytest tests/unit/ tests/integration/ -v
```

## Performance Metrics

### Before Phase 1
- VLM generic responses (truncated prompts, no fallback)
- No conflict tracking or resolution
- Failed extractions not logged or retried
- No resource awareness (OOM crashes on 8GB systems)
- No prompt validation (injection vulnerability)

### After Phase 1
- ✅ All prompts validated before VLM calls
- ✅ Cross-modal conflicts detected and resolved
- ✅ Failed extractions logged and auto-retried
- ✅ Resource-aware model selection (4.6GB → 4GB fallback)
- ✅ Audit trail for debugging and Phase 2 learning

## Deployment & Usage

### Standalone Usage

```python
from src.db.database_manager import DatabaseManager
from src.vision.adaptive_extraction import TwoStageVisionEngine
from src.core.prompt_validator import PromptValidator
from src.core.resource_monitor import ResourceMonitor
from src.core.cross_modal_validator import CrossModalValidator
from src.core.resilience_framework import ResilienceFramework

# Initialize database and components
db = DatabaseManager(root_dir="./my-project")
validator = PromptValidator()
monitor = ResourceMonitor()
reconciler = CrossModalValidator()
resilience = ResilienceFramework()

# Create vision engine with all Phase 1 features
engine = TwoStageVisionEngine(
    db=db,
    resilience=resilience,
    resource_monitor=monitor,
    prompt_validator=validator
)

# Process document pages
from src.core.data_consolidation_service import DataConsolidationService
consolidator = DataConsolidationService(db=db)

unified_context = consolidator.build_context(
    page_id=page_id,
    native_ocr=ocr_text,
    layout_metadata=layout_data
)

result = engine.process_page_two_stage(
    page_id=page_id,
    unified_context=unified_context,
    document_type="specification",
    role="engineer"
)

print(f"Reconciled: {result['reconciled']}")
print(f"Conflicts: {result['conflicts']}")
```

### With DocumentService

The standard document ingestion pipeline now includes Phase 1 components:

```python
from src.document_processing.document_service import DocumentService

service = DocumentService(db=db, project_root="./my-project")
result = service.ingest_project(
    project_id="my-project",
    root="./documents",
    recursive=True
)
# Internally uses TwoStageVisionEngine with Phase 1 features
```

## Next Steps (Phase 2)

Phase 1 establishes the data integrity and resilience foundation. **Phase 2** will leverage the audit trails to:

1. **Engineer Feedback Loop** — Collect engineer corrections and optimize prompts.
2. **Confidence Learning** — Improve model selection based on domain and task.
3. **Dynamic Prompt Engineering** — Tailor prompts to document type and role.

## Troubleshooting

### High Conflict Rates
If `data_conflicts` table shows >10% conflict rate:
- Check OCR quality: low confidence OCR may cause false conflicts
- Review Stage 1 classification: wrong document type → wrong Stage 2 prompt
- Inspect VLM model output: truncation or generic responses may indicate prompt issue

### VLM Failures
Check `failed_extractions` table for patterns:
- **Frequent timeouts**: Reduce batch size or increase model timeout
- **Truncated input**: Reduce document context size (Phase 2 task)
- **Invalid JSON**: Review Stage 2 prompt format (Phase 2 task)

### Memory Issues
Use `ResourceMonitor` to detect:
```python
from src.core.resource_monitor import ResourceMonitor
monitor = ResourceMonitor()
available = monitor.get_available_vram()
if available < 4.5:
    print(f"Insufficient memory for VLM ({available} GB); using OCR-only mode")
```

## References

- [TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md) — Full system architecture
- [src/db/migrations/001_phase1_fortification.sql](../src/db/migrations/001_phase1_fortification.sql) — Database schema SQL
- [src/core/cross_modal_validator.py](../src/core/cross_modal_validator.py) — Reconciliation service
- [src/core/resilience_framework.py](../src/core/resilience_framework.py) — Failure recovery
- [src/core/resource_monitor.py](../src/core/resource_monitor.py) — Memory management
- [src/core/prompt_validator.py](../src/core/prompt_validator.py) — Input validation
- [tests/](../tests/) — All unit and integration tests
