# -*- coding: utf-8 -*-
"""
test_placeholder_extractor_cannot_escape_staging.py

Verifies that PLACEHOLDER extractors remain isolated in STAGING_EXTRACTORS
and cannot enter the main extraction pipeline.
"""

from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.field_extractor import FieldExtractor


def test_placeholder_extractor_not_in_trusted_registry():
    """FieldExtractor (PLACEHOLDER) must not be in EXTRACTORS."""
    assert "field" not in ExtractJob.EXTRACTORS


def test_placeholder_extractor_in_staging_registry():
    """FieldExtractor (PLACEHOLDER) must be in STAGING_EXTRACTORS."""
    assert "field" in ExtractJob.STAGING_EXTRACTORS
    assert ExtractJob.STAGING_EXTRACTORS["field"] is FieldExtractor


def test_placeholder_extractor_has_place_holder_maturity():
    """FieldExtractor must declare PLACEHOLDER maturity."""
    assert FieldExtractor.maturity == "PLACEHOLDER"


def test_trusted_extractors_are_not_in_staging():
    """No PRODUCTION or VERIFIED extractor should appear in STAGING."""
    staging = set(ExtractJob.STAGING_EXTRACTORS)
    trusted = set(ExtractJob.EXTRACTORS)
    assert staging.isdisjoint(trusted)


def test_staging_extractors_have_sub_verified_maturity():
    """All STAGING_EXTRACTORS must have maturity below VERIFIED."""
    for key, cls in ExtractJob.STAGING_EXTRACTORS.items():
        assert cls.maturity in {"EXPERIMENTAL", "PLACEHOLDER"}, \
            f"{key} ({cls.__name__}) has maturity {cls.maturity} but is in STAGING"


def test_trusted_extractors_have_at_least_verified_maturity():
    """All EXTRACTORS must have maturity >= VERIFIED."""
    for key, cls in ExtractJob.EXTRACTORS.items():
        assert cls.maturity in {"PRODUCTION", "VERIFIED"}, \
            f"{key} ({cls.__name__}) has maturity {cls.maturity} but is in trusted EXTRACTORS"
