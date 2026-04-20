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
paddle_backend.py — PaddleOCR implementation
--------------------------------------------
High-quality offline OCR using PaddlePaddle.
"""

import os
import logging

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

from src.vision.ocr_backends import OCRBackend

class PaddleOCRBackend(OCRBackend):
    """
    PaddleOCR backend.
    Excellent for tables, mixed Arabic/English, and offline use.
    """

    def __init__(self, use_gpu: bool = False, lang: str = "en"):
        """
        :param use_gpu: Set to False to save VRAM for the VLM.
        :param lang: 'en', 'ar', or 'ch'. Paddle handles mixed en/ar well with lang='ar'.
        """
        if PaddleOCR is None:
            raise ImportError("paddleocr is not installed. Run: pip install paddlepaddle paddleocr")
        
        # Initialize the engine once
        # use_angle_cls=True helps with rotated text
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True, 
                lang=lang
            )
        except Exception as e:
            logging.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def recognize(self, image_path: str, lang_hint: str = "eng+ara") -> str:
        if not image_path or not os.path.exists(image_path):
            return ""

        try:
            # Use predict() as ocr() is deprecated/broken in this version
            # result structure is likely: {'rec_text': [...], 'rec_score': [...], ...} or a list of dicts
            result = self.ocr.predict(image_path)
            
            # Debug log to understand structure
            logger.debug(f"PaddleOCR result type: {type(result)}")
            logger.debug(f"PaddleOCR result content: {result}")
            
            if not result:
                return ""
            
            lines = []
            
            # Case 1: Generator
            if hasattr(result, "__iter__") and not isinstance(result, (list, dict, str)):
                result = list(result)

            # Case 2: List of dicts (common in new paddlex)
            # e.g. [{'res': {'rec_text': '...', ...}}, ...]
            if isinstance(result, list):
                for item in result:
                    # If item is a dict, look for text fields
                    if isinstance(item, dict):
                        # Try common keys
                        if "rec_texts" in item:
                            val = item["rec_texts"]
                            if isinstance(val, list):
                                lines.extend(val)
                            else:
                                lines.append(str(val))
                        elif "rec_text" in item:
                            val = item["rec_text"]
                            if isinstance(val, list):
                                lines.extend(val)
                            else:
                                lines.append(str(val))
                        elif "text" in item:
                            lines.append(item["text"])
                        elif "res" in item and isinstance(item["res"], dict):
                             if "rec_text" in item["res"]:
                                 val = item["res"]["rec_text"]
                                 if isinstance(val, list):
                                     lines.extend(val)
                                 else:
                                     lines.append(str(val))
                    # If item is a tuple/list (old format [[box, (text, score)]])
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        if isinstance(item[1], (list, tuple)) and len(item[1]) >= 1:
                            lines.append(item[1][0])

            # Case 3: Dict
            elif isinstance(result, dict):
                if "rec_texts" in result:
                     val = result["rec_texts"]
                     lines = val if isinstance(val, list) else [str(val)]
                elif "rec_text" in result:
                     val = result["rec_text"]
                     lines = val if isinstance(val, list) else [str(val)]

            return "\n".join(lines)

        except Exception as e:
            logging.error(f"PaddleOCR error: {e}")
            return f"[PaddleOCR ERROR: {str(e)}]"
