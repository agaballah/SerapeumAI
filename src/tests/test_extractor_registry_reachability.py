# -*- coding: utf-8 -*-

from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.dgn_extractor import DGNExtractor
from src.engine.extractors.pptx_extractor import PPTXExtractor
from src.engine.extractors.word_extractor import WordExtractor


def test_extract_job_registry_includes_existing_reachable_document_extractors():
    assert ExtractJob.EXTRACTORS["word"] is WordExtractor
    assert ExtractJob.EXTRACTORS["pptx"] is PPTXExtractor
    assert ExtractJob.EXTRACTORS["dgn"] is DGNExtractor


def test_extract_job_registry_keeps_existing_evidence_extractors():
    expected = {"p6", "ifc", "excel_register", "pdf", "field", "word", "pptx", "dgn"}
    assert expected.issubset(set(ExtractJob.EXTRACTORS))
