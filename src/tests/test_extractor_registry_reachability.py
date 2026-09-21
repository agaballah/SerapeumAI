# -*- coding: utf-8 -*-

from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.dgn_extractor import DGNExtractor
from src.engine.extractors.pptx_extractor import PPTXExtractor
from src.engine.extractors.word_extractor import WordExtractor
from src.engine.extractors.field_extractor import FieldExtractor
from src.engine.extractors.register_extractor import ExcelRegisterExtractor
from src.engine.extractors.pdf_extractor import UniversalPdfExtractor
from src.engine.extractors.p6_extractor import P6Extractor
from src.engine.extractors.ifc_extractor import IFCExtractor


def test_extract_job_registry_includes_existing_reachable_document_extractors():
    assert "word" in ExtractJob.EXTRACTORS
    assert ExtractJob.EXTRACTORS["word"] is WordExtractor
    assert "pptx" in ExtractJob.EXTRACTORS
    assert ExtractJob.EXTRACTORS["pptx"] is PPTXExtractor
    # DGN is now in STAGING (EXPERIMENTAL maturity), not in the trusted registry.
    assert "dgn" not in ExtractJob.EXTRACTORS


def test_extract_job_trusted_registry_keeps_production_and_verified_only():
    trusted = set(ExtractJob.EXTRACTORS)
    # PRODUCTION and VERIFIED extractors belong in the main pipeline.
    assert "p6" in trusted        # PRODUCTION
    assert "pdf" in trusted       # PRODUCTION
    assert "ifc" in trusted       # VERIFIED
    assert "word" in trusted      # VERIFIED
    assert "pptx" in trusted      # VERIFIED


def test_extract_job_staging_registry_holds_experimental_and_placeholder():
    staging = set(ExtractJob.STAGING_EXTRACTORS)
    # EXPERIMENTAL and PLACEHOLDER extractors are isolated from the main pipeline.
    assert "field" in staging            # PLACEHOLDER
    assert "excel_register" in staging   # EXPERIMENTAL
    assert "dgn" in staging              # EXPERIMENTAL


def test_extract_job_no_overlap_between_registries():
    trusted = set(ExtractJob.EXTRACTORS)
    staging = set(ExtractJob.STAGING_EXTRACTORS)
    assert trusted.isdisjoint(staging)


def test_all_extractors_have_maturity_attribute():
    all_extractors = {**ExtractJob.EXTRACTORS, **ExtractJob.STAGING_EXTRACTORS}
    for key, cls in all_extractors.items():
        assert hasattr(cls, "maturity"), f"{key} ({cls.__name__}) missing maturity class attribute"
        assert cls.maturity in {"PRODUCTION", "VERIFIED", "EXPERIMENTAL", "PLACEHOLDER"}, \
            f"{key} has invalid maturity: {cls.maturity}"
