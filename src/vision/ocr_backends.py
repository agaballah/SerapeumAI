# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ocr_backends.py — Pluggable OCR strategies
------------------------------------------
Defines the abstract base class for OCR and concrete implementations.
"""

import abc
import os

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None


class OCRBackend(abc.ABC):
    """
    Abstract base class for OCR engines.
    """

    @abc.abstractmethod
    def recognize(self, image_path: str, lang_hint: str = "eng+ara") -> str:
        """
        Perform OCR on the given image path.
        Returns the extracted text string.
        """
        pass


class TesseractBackend(OCRBackend):
    """
    Local Tesseract OCR backend.
    Requires 'pytesseract' and a local Tesseract installation.
    """

    def __init__(self):
        if not pytesseract:
            raise ImportError("pytesseract is not installed.")

    def recognize(self, image_path: str, lang_hint: str = "eng+ara") -> str:
        if not image_path or not os.path.exists(image_path):
            return ""

        try:
            # Tesseract language format is usually "eng+ara"
            # We can map generic hints if needed, but passing through is fine for now.
            text = pytesseract.image_to_string(Image.open(image_path), lang=lang_hint)
            return text.strip()
        except Exception as e:
            # Log or handle specific Tesseract errors
            return f"[OCR ERROR: {str(e)}]"


class PaddleOCRBackend(OCRBackend):
    """
    Placeholder for PaddleOCR backend.
    """
    def recognize(self, image_path: str, lang_hint: str = "eng+ara") -> str:
        return "[PaddleOCR not implemented yet]"


class CloudOCRBackend(OCRBackend):
    """
    Placeholder for Cloud OCR (Azure/GCP).
    """
    def recognize(self, image_path: str, lang_hint: str = "eng+ara") -> str:
        return "[CloudOCR not implemented yet]"
