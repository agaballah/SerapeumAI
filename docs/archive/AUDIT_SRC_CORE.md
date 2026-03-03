# Audit: src/core/ (Line-by-Line)

This document contains the exhaustive investigation of the `src/core/` directory.

## 📄 [resource_monitor.py](file:///d:/SerapeumAI/src/core/resource_monitor.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 30 | Safety Margin | Hardcoded 15% reserve | Move to `config.yaml`. |
| 48 | NVML Init | Repeated initialization | Initialize once in `__init__` or use a singleton pattern for performance. |
| 94-98 | Resource Score | `vram + ram` sum | Upgrade to weighted score (e.g., `vram * 5 + ram`) to reflect VRAM scarcity. |
| 104-124 | Throttle Logic | Ratio-based pressure check | Support project-specific memory pressure policies. |

---

## 📄 [model_selector.py](file:///d:/SerapeumAI/src/core/model_selector.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 22-32 | Static Mappings | Roles/Disciplines validation | Move to project-wide `consts.py` or `schema.yaml`. |
| 220-225 | Role Thresholds | Policy-based safety gates | Externalize values to `config.yaml` for project-specific tuning. |
| 230-236 | Discipline Adjusts | Safety-criticality weighting | Link to a centralized `discipline_meta.yaml`. |
| 301-358 | Strategy Dictionary | Role-based instructions | **CRITICAL**: Move to external `strategies.yaml`; hardcoding complicates updates. |
| 371-402 | Model Catalog | VRAM/RAM specs | Move to `models.yaml`; allows adding new models without code changes. |
| 406-488 | Discipline Maps | Field importance/thresholds | Relocate to external configuration file. |
| 510-524 | Selection Boosts | Model recommendation weights | Replace hardcoded scores with metrics-driven weights from `ConfidenceLearner`. |
| 560 | Selection Logic | Simple "largest fits" sort | Implement a scorecard-based selection (Latency vs. Accuracy trade-off). |

---

## 📄 [correction_collector.py](file:///d:/SerapeumAI/src/core/correction_collector.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 17-25 | `FeedbackType` Enum | Categorizes AECO errors (Typos, Wrong Class, etc.) | None. |
| 35-46 | `CorrectionRecord` | Data structure for human-in-the-loop feedback | Upgrade to Pydantic for stricter validation. |
| 88-143 | `collect_corrections` | DB retrieval logic for corrections | Standardize error handling; avoid raw SQL; use specific DB exceptions. |
| 144-202 | `compute_correction_metrics` | Aggregates error statistics | Standardize metric schemas; ensure 0-1 normalization. |
| 232 | `_get_extraction_count` | Simplified lookups for denominator | Replace expensive SQL `COUNT` with cached metadata or accuracy tables. |
| 346-358 | Recommendation logic | Hardcoded rules for model switching | Move thresholds (0.3, 0.05) to `config.yaml`. |
| 376-378 | `_compute_trend` | Arbitrary 0.1 delta for trend detection | Replace with statistical significance test (e.g., T-test or Chi-square). |
| 407 | `_extract_error_patterns` | Simple string slicing `[:50]` | Implement N-gram analysis or fuzzy clustering for real pattern detection. |
| 445-446 | Bayesian Smoothing | Manual `len + 10` smoothing | Formalize as a Bayesian prior calculation ($ \alpha, \beta $ beta distribution). |

---

## 📄 [confidence_learner.py](file:///d:/SerapeumAI/src/core/confidence_learner.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 18-24 | `ConfidenceLevel` | Domain-specific quality bins | Synchronize boundaries with project-wide safety policies. |
| 84-85 | In-memory Caches | Performance/Profile storage | **CRITICAL**: Move to Redis or DB; current state loses learning on restart. |
| 129-131 | Learning Increments | Model accuracy updates | Replace `+/- 0.1` with Exponential Moving Average (EMA). |
| 147-149 | Accuracy Increments | Field difficulty updates | Use Bayesian priors ($ \mu, \sigma $) instead of linear steps. |
| 185-186 | Confidence Blending | Final score calculation | Replace hardcoded `0.6/0.4` with precision-weighted blending. |
| 310 | Accuracy Estimation | Simple ratio calculation | Implement Wilson score interval for better small-sample handling. |
| 420-424 | VRAM Thresholds | Model recommendation | Move to `config.yaml` or dynamic `ResourceMonitor` lookup. |
| 439 | Readiness Heuristics| Maturity estimation | Refine with statistical confidence intervals on global accuracy. |
| 478 | `avg_vlm_conf` | Static placeholder | Replace with real historical averages from DB. |
