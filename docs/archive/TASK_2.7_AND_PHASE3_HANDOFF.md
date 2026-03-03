# TASK 2.7 & Phase 3 Handoff: Documentation and Safety/Observability

**Status:** NOT STARTED  
**Last Updated:** 2025-01-27  
**Effort Estimate:** 15-25 hours total
**Sequence:** TASK 2.7 first (2-3 hrs), then Phase 3.1-3.3 (12-20 hrs)

---

## Table of Contents
1. [TASK 2.7: Phase 2 Documentation](#task-27-phase-2-documentation) (2-3 hours)
2. [Phase 3.1: Validation Safety Gates](#phase-31-validation-safety-gates) (6-8 hours)
3. [Phase 3.2: Observability & Telemetry](#phase-32-observability--telemetry) (4-6 hours)
4. [Phase 3.3: Safety Integration Tests](#phase-33-safety-integration-tests) (2-3 hours)

---

# TASK 2.7: Phase 2 Documentation

**Status:** NOT STARTED  
**Time Estimate:** 2-3 hours  
**Output:** PHASE2_ARCHITECTURE.md + README updates

## Objectives

Create comprehensive documentation of Phase 2 feedback loop system, similar in scope/quality to PHASE1_ARCHITECTURE.md. Must cover:
- Architecture and component interactions
- Feedback loop mechanics (correction → learning → optimization → selection)
- Role and discipline adaptation system
- Integration guide and usage examples
- API reference for developers

## Deliverables

### 1. PHASE2_ARCHITECTURE.md (600-800 lines)

**Location:** `docs/PHASE2_ARCHITECTURE.md`

**Structure:**

```markdown
# Phase 2: Engineer Feedback Loop Architecture

## Table of Contents
1. Overview & Motivation
2. System Architecture
3. Component Deep Dives
4. Feedback Loop Mechanics
5. Role & Discipline Adaptation
6. Integration Guide
7. API Reference
8. Performance Considerations
9. Known Limitations

### 1. Overview & Motivation (100 lines)
- Why feedback loop matters (learning from corrections)
- High-level flow diagram (text-based)
- Phase 1 → Phase 2 progression
- Key improvements over Phase 1

### 2. System Architecture (150 lines)
- Component diagram (ASCII art or reference external)
- Data flow through 4 components
- Feedback mechanism
- Caching and optimization strategies
- Role of correction collector as feedback aggregator

### 3. Component Deep Dives (200 lines total)

#### 3.1 CorrectionCollector
- Purpose: Aggregate engineer corrections
- FeedbackType system (all 6 types with examples)
- Metrics computation
- Problem area identification
- Usage: `collector.collect_corrections()`, `identify_problem_areas()`

#### 3.2 ConfidenceLearner
- Purpose: Learn extraction accuracy per field/model
- Tracking mechanism: `track_extraction()`
- Field confidence profiles
- Model performance profiles
- Usage: `compute_learned_confidence()`

#### 3.3 PromptOptimizer
- Purpose: Generate optimized, role/discipline-aware prompts
- Two-stage prompt generation
- Few-shot example selection
- Dynamic adjustments based on performance
- Usage: `generate_stage1_prompt()`, `generate_stage2_prompt()`

#### 3.4 ModelSelector
- Purpose: Select best LLM model for role/discipline/field
- Role-based thresholds and preferences
- Discipline-specific model recommendations
- Field-level performance tracking
- Usage: `select_model_for_role_discipline()`

### 4. Feedback Loop Mechanics (100 lines)
- Correction → Learning flow
- Learning → Prompt Optimization flow
- Optimization → Model Selection flow
- Closed loop: Selection → Next Extraction → Correction
- Example walkthrough: panel_size extraction over 3 iterations

### 5. Role & Discipline Adaptation (100 lines)
- Role definitions: Contractor, Technical Consultant, Owner, Supervisor
- Discipline definitions: Arch, Elec, Mech, Str
- Role-specific thresholds (accuracy confidence levels)
- Discipline-specific model preferences
- Cross-role adaptation

### 6. Integration Guide (50 lines)
- Using all 4 components together
- Order of operations
- Data passing between components
- State management
- Example code snippet: full feedback loop

### 7. API Reference (100 lines)
- All public methods
- Parameter details
- Return types
- Example usage for each

### 8. Performance Considerations (50 lines)
- Caching strategies
- Memory footprint
- Processing speed
- Scalability notes

### 9. Known Limitations (50 lines)
- Field profile caching (optional feature)
- Model metadata limitations
- Correction history limitations
- Future improvements
```

**Content Guidelines:**
- Use actual component code references
- Include concrete examples from real fields (panel_size, wire_gauge, etc.)
- Show FeedbackType enum with all 6 values
- Include ASCII diagrams where helpful
- Cross-reference to API docs and source code
- Match tone/style of PHASE1_ARCHITECTURE.md

### 2. Update README.md

**Sections to Add:**

```markdown
## Phase 2: Engineer Feedback Loop (NEW)

Implements a closed-loop learning system where engineer corrections drive improvement:
- **Correction Collection:** Aggregate and categorize engineer feedback
- **Confidence Learning:** Track model accuracy per field/discipline
- **Prompt Optimization:** Generate context-aware prompts with few-shot examples
- **Model Selection:** Choose optimal LLM based on role, discipline, and history

See [Phase 2 Architecture](docs/PHASE2_ARCHITECTURE.md) for detailed documentation.

### Quick Start: Using the Feedback Loop

[code example here]
```

**Update Sections:**
- Add Phase 2 to project phases section
- Add link to PHASE2_ARCHITECTURE.md
- Quick reference to 4 main components
- Link to integration tests

### 3. Create Integration Guide

**File:** `docs/INTEGRATION_GUIDE.md` (optional, can be appendix of PHASE2_ARCHITECTURE.md)

**Content:**
- Step-by-step integration of all 4 Phase 2 components
- Code examples
- Common patterns
- Troubleshooting

## Reference Materials

### Phase 1 Documentation (Use as Template)
- [PHASE1_ARCHITECTURE.md](docs/PHASE1_ARCHITECTURE.md) - 600+ line reference
- Style, depth, and structure to match

### Component Source Files
- [correction_collector.py](src/core/correction_collector.py) - FeedbackType, metrics
- [confidence_learner.py](src/core/confidence_learner.py) - learning mechanics
- [prompt_optimizer.py](src/core/prompt_optimizer.py) - prompt generation
- [model_selector.py](src/core/model_selector.py) - model selection logic

### Unit Tests (For Examples)
- All tests in `tests/unit/` directory - show realistic usage patterns

## Documentation Checklist

- [ ] PHASE2_ARCHITECTURE.md created (600+ lines)
- [ ] All 4 components documented with purpose/usage
- [ ] All 6 FeedbackType values explained with examples
- [ ] Role definitions documented (Contractor, Technical Consultant, Owner, Supervisor)
- [ ] Discipline definitions documented (Arch, Elec, Mech, Str)
- [ ] Code examples included (copy from unit tests)
- [ ] ASCII diagrams or reference to external diagrams
- [ ] Cross-references to source code
- [ ] Performance notes included
- [ ] Known limitations documented
- [ ] README.md updated with Phase 2 section
- [ ] Integration guide created or included as appendix
- [ ] All links working and paths correct
- [ ] Consistent formatting with Phase 1 doc
- [ ] Reviewed for completeness

---

# Phase 3: Safety & Observability

**Total Effort:** 12-20 hours  
**Architecture:** Safety gates → Observability infrastructure → Integration tests

---

# Phase 3.1: Validation Safety Gates

**Status:** NOT STARTED  
**Time Estimate:** 6-8 hours  
**Output:** `src/core/safety/` with validation system

## Objectives

Implement safety mechanisms to:
1. Detect extraction errors and anomalies
2. Provide recovery mechanisms
3. Prevent propagation of bad extractions
4. Flag uncertain extractions for review

## Architecture

```
CorrectionCollector
      ↓
SafetyValidator
  ├─ AnomalyDetector (field-level anomalies)
  ├─ ConsistencyValidator (cross-field validation)
  └─ ConfidenceGate (confidence-based flagging)
      ↓
Safe Extraction → Next Phase
Unsafe Extraction → Quarantine/Review Queue
```

## Implementation Tasks

### Task 3.1.1: Create Safety Module Structure

**Location:** `src/core/safety/`

**Files to Create:**
```
src/core/safety/
├── __init__.py
├── safety_validator.py       (main orchestrator)
├── anomaly_detector.py       (field-level checks)
├── consistency_validator.py  (cross-field checks)
├── confidence_gate.py        (confidence-based gating)
└── safety_types.py          (enums and dataclasses)
```

### Task 3.1.2: SafetyValidator (Orchestrator)

**Purpose:** Central safety orchestration

**File:** `src/core/safety/safety_validator.py` (100-150 lines)

**Key Methods:**
```python
class SafetyValidator:
    """Orchestrates all safety checks."""
    
    def __init__(self, 
                 confidence_learner=None,
                 anomaly_detector=None,
                 consistency_validator=None,
                 confidence_gate=None):
        """Initialize with components."""
        pass
    
    def validate_extraction(self, 
                           field_name: str,
                           extracted_value: str,
                           document_type: str,
                           vlm_confidence: float,
                           model_used: str) -> ValidationResult:
        """
        Run full validation pipeline on extracted value.
        
        Returns: ValidationResult with is_safe, flags, recommendations
        """
        pass
    
    def validate_batch_extractions(self,
                                   extractions: List[ExtractedField]) -> List[ValidationResult]:
        """Validate multiple extractions."""
        pass
    
    def get_safety_report(self) -> SafetyReport:
        """Generate comprehensive safety report."""
        pass
```

**ValidationResult Structure:**
```python
@dataclass
class ValidationResult:
    field_name: str
    is_safe: bool
    confidence_level: str  # "safe", "warning", "critical"
    flags: List[str]       # ["anomaly_detected", "low_confidence", ...]
    recommendations: List[str]  # ["require_review", "use_qwen2", ...]
    details: Dict[str, Any]  # Detailed findings
    timestamp: datetime
```

### Task 3.1.3: AnomalyDetector

**Purpose:** Detect field-level anomalies

**File:** `src/core/safety/anomaly_detector.py` (150-200 lines)

**Detection Strategies:**
```python
class AnomalyDetector:
    """Detects field-level anomalies."""
    
    def detect_anomalies(self,
                        field_name: str,
                        extracted_value: str,
                        document_type: str,
                        vlm_confidence: float) -> List[Anomaly]:
        """
        Detect anomalies:
        - Out-of-range values (e.g., -10A for panel_size)
        - Invalid formats (e.g., "XXXX" for wire_gauge)
        - Impossible combinations (e.g., "Sub-panel" > "Main panel")
        - Confidence anomalies (e.g., 0.99 confidence but value changed 5x)
        - Statistical outliers based on historical data
        """
        pass
    
    def _check_value_range(self, field: str, value: str) -> Optional[Anomaly]:
        """Check if value in valid range for field."""
        pass
    
    def _check_format(self, field: str, value: str) -> Optional[Anomaly]:
        """Check if value matches expected format."""
        pass
    
    def _check_statistical_outlier(self, field: str, value: str) -> Optional[Anomaly]:
        """Detect statistical outliers."""
        pass
```

**Anomaly Types:**
```python
class AnomalyType(Enum):
    INVALID_FORMAT = "invalid_format"          # Wrong pattern
    OUT_OF_RANGE = "out_of_range"             # Value outside domain
    INCONSISTENT_CONFIDENCE = "inconsistent_confidence"  # Mismatch
    STATISTICAL_OUTLIER = "statistical_outlier"  # Unusual value
    MODEL_UNCERTAINTY = "model_uncertainty"    # Multiple guesses from model
    IMPOSSIBLE_COMBINATION = "impossible_combination"  # Cross-field impossible
```

### Task 3.1.4: ConsistencyValidator

**Purpose:** Validate cross-field consistency

**File:** `src/core/safety/consistency_validator.py` (100-150 lines)

**Consistency Rules:**
```python
class ConsistencyValidator:
    """Validates cross-field consistency."""
    
    def validate_consistency(self,
                            extractions: Dict[str, str],
                            document_type: str) -> List[ConsistencyIssue]:
        """
        Check:
        - Breaker size ≤ panel_size
        - Wire gauge matches amperage
        - Sub-panel size ≤ main panel size
        - Equipment count matches schedule
        """
        pass
    
    def add_consistency_rule(self, rule: ConsistencyRule):
        """Add custom consistency rule."""
        pass
```

**Consistency Rules Database:**
```python
CONSISTENCY_RULES = {
    "Elec": [
        ConsistencyRule(
            name="breaker_size_vs_panel",
            check=lambda extr: float(extr.get("breaker_size", 0)) <= float(extr.get("panel_size", 0)),
            message="Breaker size must be ≤ panel size"
        ),
        # ... more rules
    ],
    "Mech": [
        # Mechanical consistency rules
    ],
}
```

### Task 3.1.5: ConfidenceGate

**Purpose:** Flag extractions based on confidence thresholds

**File:** `src/core/safety/confidence_gate.py` (80-120 lines)

**Implementation:**
```python
class ConfidenceGate:
    """Gates extractions based on confidence thresholds."""
    
    def evaluate_gate(self,
                     field_name: str,
                     vlm_confidence: float,
                     model_used: str,
                     role: str,
                     discipline: str,
                     confidence_learner=None) -> GateDecision:
        """
        Evaluate if extraction should pass confidence gate:
        - Field-specific learned thresholds
        - Role-based requirements
        - Model-specific calibration
        - Confidence trend analysis
        """
        pass
    
    def get_confidence_requirement(self,
                                  field_name: str,
                                  role: str,
                                  discipline: str) -> float:
        """Get required confidence level."""
        pass
```

**GateDecision:**
```python
@dataclass
class GateDecision:
    passed: bool
    confidence_required: float
    confidence_observed: float
    gap: float  # required - observed
    recommendation: str  # "accept", "review", "reject", "retract_with_qa"
```

### Task 3.1.6: Safety Types

**File:** `src/core/safety/safety_types.py` (80-100 lines)

**Enums and Dataclasses:**
```python
@dataclass
class Anomaly:
    type: AnomalyType
    severity: str  # "low", "medium", "high"
    message: str
    field_name: str
    details: Dict[str, Any]

@dataclass
class ConsistencyIssue:
    rule_name: str
    fields_involved: List[str]
    severity: str
    message: str
    recommendation: str

@dataclass
class SafetyReport:
    total_extractions: int
    safe_extractions: int
    flagged_extractions: int
    safety_score: float  # 0-1
    critical_issues: List[Anomaly]
    warnings: List[Anomaly]
    timestamp: datetime
```

## Unit Tests for Safety

**File:** `tests/unit/test_safety_validator.py` (200-250 lines)

**Test Classes:**
```python
class TestAnomalyDetector:
    """Test anomaly detection."""
    - test_detect_invalid_format()
    - test_detect_out_of_range()
    - test_detect_statistical_outlier()
    - test_skip_valid_values()

class TestConsistencyValidator:
    """Test cross-field consistency."""
    - test_breaker_size_vs_panel_consistency()
    - test_wire_gauge_vs_amperage_consistency()
    - test_skip_consistent_values()

class TestConfidenceGate:
    """Test confidence-based gating."""
    - test_pass_high_confidence()
    - test_flag_low_confidence()
    - test_role_specific_thresholds()

class TestSafetyValidator:
    """Test orchestration."""
    - test_full_validation_pipeline()
    - test_batch_validation()
    - test_safety_report_generation()
```

## Safety Validation Checklist

- [ ] SafetyValidator orchestrator created
- [ ] AnomalyDetector implemented with 5+ check types
- [ ] ConsistencyValidator with rule database
- [ ] ConfidenceGate with learned thresholds
- [ ] All dataclasses and enums defined
- [ ] Unit tests: 100+ tests, all passing
- [ ] Integration with ConfidenceLearner
- [ ] Performance validated (< 50ms per extraction)
- [ ] Documentation in docstrings

---

# Phase 3.2: Observability & Telemetry

**Status:** NOT STARTED  
**Time Estimate:** 4-6 hours  
**Output:** `src/telemetry/` with metrics and logging

## Objectives

Implement comprehensive observability:
1. Extraction metrics (accuracy, confidence, speed)
2. Model performance tracking
3. Field-level performance trends
4. System health metrics
5. Detailed logging for debugging

## Architecture

```
Phase 2 Components + Safety Gates
           ↓
MetricsCollector (aggregates events)
    ├─ ExtractionMetrics
    ├─ ModelMetrics
    ├─ FieldMetrics
    └─ SystemMetrics
           ↓
LoggerFactory (structured logging)
    ├─ ExtractionLogger
    ├─ PerformanceLogger
    └─ ErrorLogger
           ↓
MetricsStore (persistence)
    ├─ SQLite storage
    └─ JSON export
```

## Implementation Tasks

### Task 3.2.1: Create Telemetry Module

**Location:** `src/telemetry/`

**Files to Create:**
```
src/telemetry/
├── __init__.py
├── metrics_collector.py      (main orchestrator)
├── metrics_types.py         (all metric dataclasses)
├── logger_factory.py        (structured logging)
├── metrics_store.py         (persistence)
└── telemetry_config.py      (configuration)
```

### Task 3.2.2: MetricsCollector

**File:** `src/telemetry/metrics_collector.py` (150-200 lines)

**Purpose:** Collect and aggregate metrics

**Key Methods:**
```python
class MetricsCollector:
    """Collects extraction and system metrics."""
    
    def __init__(self, db=None):
        self.db = db
        self.session_metrics = SessionMetrics()
        self.field_metrics = {}
        self.model_metrics = {}
    
    def record_extraction(self,
                         field_name: str,
                         model_used: str,
                         vlm_confidence: float,
                         extracted_value: str,
                         was_correct: Optional[bool] = None,
                         processing_time_ms: float = 0,
                         safety_flags: List[str] = None):
        """Record single extraction with metrics."""
        pass
    
    def get_field_metrics(self, field_name: str) -> FieldMetrics:
        """Get aggregated metrics for field."""
        pass
    
    def get_model_metrics(self, model_name: str) -> ModelMetrics:
        """Get aggregated metrics for model."""
        pass
    
    def get_session_metrics(self) -> SessionMetrics:
        """Get current session metrics."""
        pass
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics (json or csv)."""
        pass
```

### Task 3.2.3: Metrics Types

**File:** `src/telemetry/metrics_types.py` (150-200 lines)

**Metric Dataclasses:**
```python
@dataclass
class ExtractionMetric:
    """Single extraction metric."""
    timestamp: datetime
    field_name: str
    model_used: str
    vlm_confidence: float
    was_correct: Optional[bool]
    processing_time_ms: float
    safety_flags: List[str]
    extraction_id: str

@dataclass
class FieldMetrics:
    """Aggregated metrics for field."""
    field_name: str
    total_extractions: int
    successful_extractions: int
    accuracy: float  # 0-1
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    avg_processing_time_ms: float
    safety_flag_rate: float
    confidence_trend: str  # "improving", "stable", "declining"
    best_model: str
    worst_model: str

@dataclass
class ModelMetrics:
    """Aggregated metrics for model."""
    model_name: str
    total_extractions: int
    accuracy: float
    avg_confidence: float
    confidence_calibration: float  # How well confidence predicts accuracy
    avg_processing_time_ms: float
    fields_most_accurate: List[Tuple[str, float]]
    fields_most_inaccurate: List[Tuple[str, float]]

@dataclass
class SessionMetrics:
    """Current session metrics."""
    session_id: str
    start_time: datetime
    total_extractions: int
    success_rate: float
    avg_confidence: float
    errors: int
    warnings: int
    total_processing_time_ms: float
```

### Task 3.2.4: LoggerFactory

**File:** `src/telemetry/logger_factory.py` (120-160 lines)

**Purpose:** Structured logging for debugging

**Implementation:**
```python
class LoggerFactory:
    """Factory for creating structured loggers."""
    
    @staticmethod
    def get_extraction_logger() -> logging.Logger:
        """Logger for extraction events."""
        pass
    
    @staticmethod
    def get_performance_logger() -> logging.Logger:
        """Logger for performance metrics."""
        pass
    
    @staticmethod
    def get_error_logger() -> logging.Logger:
        """Logger for errors and warnings."""
        pass
    
    @staticmethod
    def get_safety_logger() -> logging.Logger:
        """Logger for safety events."""
        pass
```

**Log Structures:**
```
Extraction Log:
{
    "timestamp": "2025-01-27T10:00:00Z",
    "event": "extraction_complete",
    "field_name": "panel_size",
    "model": "Qwen2-VL-7B",
    "confidence": 0.92,
    "value": "200A",
    "processing_time_ms": 125,
    "safety_flags": []
}

Performance Log:
{
    "timestamp": "2025-01-27T10:00:00Z",
    "metric": "field_accuracy",
    "field": "wire_gauge",
    "accuracy": 0.94,
    "sample_size": 127
}

Error Log:
{
    "timestamp": "2025-01-27T10:00:00Z",
    "level": "WARNING",
    "event": "anomaly_detected",
    "details": {...}
}
```

### Task 3.2.5: MetricsStore

**File:** `src/telemetry/metrics_store.py` (100-150 lines)

**Purpose:** Persist metrics

**Implementation:**
```python
class MetricsStore:
    """Persists metrics to database."""
    
    def __init__(self, db=None):
        self.db = db
    
    def save_extraction_metric(self, metric: ExtractionMetric):
        """Save extraction to database."""
        pass
    
    def query_field_metrics(self, 
                           field_name: str,
                           start_date: datetime = None,
                           end_date: datetime = None) -> FieldMetrics:
        """Query field metrics from database."""
        pass
    
    def generate_report(self, 
                       report_type: str) -> str:
        """Generate HTML/PDF report."""
        pass
```

**Database Schema:**
```sql
CREATE TABLE extraction_metrics (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    field_name VARCHAR,
    model_used VARCHAR,
    vlm_confidence FLOAT,
    was_correct BOOLEAN,
    processing_time_ms FLOAT,
    safety_flags JSON,
    FOREIGN KEY (field_name) REFERENCES fields(name),
    FOREIGN KEY (model_used) REFERENCES models(name)
);

CREATE TABLE field_metrics_cache (
    field_name VARCHAR PRIMARY KEY,
    total_extractions INTEGER,
    accuracy FLOAT,
    avg_confidence FLOAT,
    last_updated DATETIME
);
```

## Unit Tests for Telemetry

**File:** `tests/unit/test_telemetry.py` (150-200 lines)

**Test Classes:**
```python
class TestMetricsCollector:
    - test_record_extraction()
    - test_field_metrics_aggregation()
    - test_model_metrics_aggregation()
    - test_accuracy_calculation()
    - test_confidence_trend_detection()
    - test_metrics_export()

class TestLoggerFactory:
    - test_extraction_logger()
    - test_performance_logger()
    - test_error_logger()

class TestMetricsStore:
    - test_save_extraction_metric()
    - test_query_metrics()
    - test_report_generation()
```

## Telemetry Integration Checklist

- [ ] MetricsCollector created with aggregation logic
- [ ] All metric dataclasses defined
- [ ] LoggerFactory with 4 logger types
- [ ] MetricsStore with database persistence
- [ ] Unit tests: 50+ tests, all passing
- [ ] Integration with Phase 2 components
- [ ] Logging to `logs/app.jsonl`
- [ ] Performance: < 5ms overhead per extraction
- [ ] Documentation in docstrings

---

# Phase 3.3: Safety Integration Tests

**Status:** NOT STARTED  
**Time Estimate:** 2-3 hours  
**Output:** Integration tests for safety + observability

## Objectives

End-to-end tests for:
1. Safety gates preventing bad extractions
2. Observability tracking full pipeline
3. Combined Phase 2 + Phase 3 workflow

## Test File

**Location:** `tests/integration/test_phase3_safety_and_observability.py`

**Test Classes:**

```python
class TestSafetyGateIntegration:
    """Test safety gates with learning and model selection."""
    
    def test_anomaly_triggers_manual_review_flag(self):
        """Anomaly detection flags extraction for manual review."""
        pass
    
    def test_consistency_check_prevents_impossible_values(self):
        """Consistency rules prevent impossible field combinations."""
        pass
    
    def test_confidence_gate_respects_learned_thresholds(self):
        """Gates adjust based on confidence learning."""
        pass
    
    def test_failed_safety_gates_recommend_model_switch(self):
        """Safety failures trigger model selection review."""
        pass

class TestObservabilityIntegration:
    """Test metrics collection across pipeline."""
    
    def test_extraction_to_metrics_flow(self):
        """Extractions generate proper metrics."""
        pass
    
    def test_field_metrics_aggregation(self):
        """Metrics aggregated correctly per field."""
        pass
    
    def test_model_metrics_track_accuracy(self):
        """Model performance tracked accurately."""
        pass
    
    def test_logging_to_structured_logs(self):
        """All events logged to structured logs."""
        pass

class TestPhase2Phase3Integration:
    """Test Phase 2 + Phase 3 together."""
    
    def test_full_pipeline_with_safety_and_observability(self):
        """Complete flow: extraction → safety → learning → optimization → observation."""
        pass
    
    def test_safety_gates_interact_with_feedback_loop(self):
        """Safety and feedback loop work together."""
        pass
    
    def test_observability_tracks_safety_effectiveness(self):
        """Metrics track how well safety gates work."""
        pass
```

## Integration Test Checklist

- [ ] 10+ integration tests created
- [ ] Tests verify safety gate functionality
- [ ] Tests verify observability functionality
- [ ] Tests verify Phase 2 + Phase 3 integration
- [ ] All tests passing
- [ ] Performance acceptable (< 1s per test)

---

# Summary: What Needs to Be Done

## TASK 2.7: Phase 2 Documentation (2-3 hours)
```
┌─────────────────────────────────────────────────┐
│ Create PHASE2_ARCHITECTURE.md (600+ lines)      │
│ ├─ Overview & motivation                        │
│ ├─ System architecture                          │
│ ├─ Component deep dives (4 components)          │
│ ├─ Feedback loop mechanics                      │
│ ├─ Role & discipline adaptation                 │
│ ├─ Integration guide                            │
│ ├─ API reference                                │
│ ├─ Performance considerations                   │
│ └─ Known limitations                            │
│                                                 │
│ Update README.md with Phase 2 section           │
│ Create Integration Guide (optional)             │
└─────────────────────────────────────────────────┘
```

## Phase 3.1: Safety Gates (6-8 hours)
```
┌──────────────────────────────────────────────────┐
│ src/core/safety/                                 │
│ ├─ safety_validator.py (orchestrator)           │
│ ├─ anomaly_detector.py (5+ detection types)     │
│ ├─ consistency_validator.py (cross-field rules) │
│ ├─ confidence_gate.py (threshold gating)        │
│ └─ safety_types.py (enums and dataclasses)      │
│                                                  │
│ tests/unit/test_safety_validator.py (100+ tests)│
│                                                  │
│ Validates: format, range, consistency, anomalies│
└──────────────────────────────────────────────────┘
```

## Phase 3.2: Observability (4-6 hours)
```
┌──────────────────────────────────────────────────┐
│ src/telemetry/                                   │
│ ├─ metrics_collector.py (aggregation)           │
│ ├─ metrics_types.py (dataclasses)               │
│ ├─ logger_factory.py (structured logging)       │
│ ├─ metrics_store.py (persistence)               │
│ └─ telemetry_config.py (configuration)          │
│                                                  │
│ tests/unit/test_telemetry.py (50+ tests)       │
│                                                  │
│ Tracks: accuracy, confidence, speed, safety     │
└──────────────────────────────────────────────────┘
```

## Phase 3.3: Integration Tests (2-3 hours)
```
┌────────────────────────────────────────────────┐
│ tests/integration/                             │
│ └─ test_phase3_safety_and_observability.py     │
│    ├─ Safety gate integration (4 tests)        │
│    ├─ Observability integration (4 tests)      │
│    └─ Phase 2 + Phase 3 integration (3 tests)  │
│                                                │
│ Validates: end-to-end flows work together     │
└────────────────────────────────────────────────┘
```

---

# Development Priority

**Sequence:**
1. **TASK 2.7 First** (2-3 hours)
   - Unblock Phase 3
   - Document Phase 2
   - Easy wins

2. **Phase 3.1** (6-8 hours)
   - Foundation for Phase 3
   - Most complex feature
   - Critical safety functionality

3. **Phase 3.2** (4-6 hours)
   - Depends on Phase 3.1
   - Adds observability to safety

4. **Phase 3.3** (2-3 hours)
   - Validates everything works
   - Can run in parallel with 3.2

**Total Timeline:** 15-25 hours (~2-3 days for 1 developer)

---

# Key References

## Existing Similar Code
- [PHASE1_ARCHITECTURE.md](docs/PHASE1_ARCHITECTURE.md) - style reference
- [test_correction_collector.py](tests/unit/test_correction_collector.py) - test patterns
- [logging_architecture.md](docs/LOGGING_ARCHITECTURE.md) - logging reference

## External Standards
- [Python logging best practices](https://docs.python.org/3/library/logging.html)
- [Dataclass documentation](https://docs.python.org/3/library/dataclasses.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/) for database (if used)

---

# Success Criteria

## TASK 2.7 Complete When:
- ✅ PHASE2_ARCHITECTURE.md: 600+ lines, well-structured
- ✅ All 4 components documented with examples
- ✅ All FeedbackType enum values explained
- ✅ Role/discipline system documented
- ✅ README.md updated
- ✅ Links verified, formatting consistent

## Phase 3.1 Complete When:
- ✅ 100+ unit tests passing
- ✅ 5+ anomaly detection types working
- ✅ Consistency rule system functional
- ✅ Confidence gating integrated with learning
- ✅ Performance: < 50ms per validation

## Phase 3.2 Complete When:
- ✅ 50+ unit tests passing
- ✅ Metrics aggregation working
- ✅ Structured logging functional
- ✅ Database persistence working
- ✅ Performance: < 5ms overhead per extraction

## Phase 3.3 Complete When:
- ✅ 10+ integration tests passing
- ✅ Safety gates prevent bad extractions
- ✅ Observability tracks full pipeline
- ✅ Phase 2 + Phase 3 work together seamlessly
- ✅ All performance targets met

---

# Questions for Handoff

1. Should safety validation be mandatory or optional per extraction?
2. Are there domain-specific anomaly rules beyond examples provided?
3. Should metrics be stored in database or in-memory only during session?
4. What's the SLA for extraction processing time with safety/observability?
5. Should there be a web dashboard for viewing metrics?

---

**Status:** Ready for new developer  
**Last Updated:** 2025-01-27  
**Effort Remaining:** 15-25 hours
