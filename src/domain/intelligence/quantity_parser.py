# -*- coding: utf-8 -*-
"""
PhysicalQuantityParser - Unit-aware parsing and comparison for AECO engineering
Uses the `pint` library to ensure mathematical correctness across units (e.g. mm, m, ft).
"""

import logging
from typing import Tuple, Optional, Union
try:
    from pint import UnitRegistry, Quantity
    ureg = UnitRegistry()
except ImportError:
    ureg = None
    Quantity = None

logger = logging.getLogger(__name__)

class PhysicalQuantityParser:
    """
    Expert utility for parsing and comparing engineering quantities with unit awareness.
    """
    
    def __init__(self):
        self.ureg = ureg
        if not self.ureg:
            logger.warning("Pint not installed. PhysicalQuantityParser will fallback to simple float conversion.")

    def parse(self, value_str: str) -> Optional[Union[float, 'Quantity']]:
        """
        Parse a string like '5mm' or '10.5 m' into a Pint Quantity or float.
        """
        if not value_str or not isinstance(value_str, str):
            return None
            
        value_str = value_str.strip()
        if not value_str:
            return None

        if not self.ureg:
            # Fallback: remove letters and try float
            import re
            numeric_part = re.sub(r'[^0-9.]', '', value_str)
            try:
                return float(numeric_part)
            except ValueError:
                return None

        try:
            return self.ureg(value_str)
        except Exception as e:
            logger.debug(f"Failed to parse quantity '{value_str}': {e}")
            # Try numeric fallback
            import re
            numeric_part = re.sub(r'[^0-9.]', '', value_str)
            try:
                return float(numeric_part)
            except ValueError:
                return None

    def compare_within_tolerance(self, 
                               val1: Union[str, float, 'Quantity'], 
                               val2: Union[str, float, 'Quantity'], 
                               tolerance: Union[str, float, 'Quantity']) -> bool:
        """
        Compare two values and return True if they are within the specified tolerance.
        Handles unit conversion automatically (e.g. 5mm vs 0.005m).
        """
        q1 = self.parse(val1) if isinstance(val1, str) else val1
        q2 = self.parse(val2) if isinstance(val2, str) else val2
        tol = self.parse(tolerance) if isinstance(tolerance, str) else tolerance

        if q1 is None or q2 is None or tol is None:
            return False

        # If not using Pint, do simple float comparison
        if not self.ureg:
            try:
                return abs(float(q1) - float(q2)) <= float(tol)
            except (ValueError, TypeError):
                return False

        try:
            # Check if units are compatible
            diff = q1 - q2
            return abs(diff) <= tol
        except Exception as e:
            logger.error(f"Unit mismatch or comparison error for {q1}, {q2}, {tol}: {e}")
            return False

    def is_consistent(self, measured: str, specified: str, allowed_margin: str = "1%") -> bool:
        """
        Check if a measured value is consistent with a specified value within a percentage or absolute margin.
        """
        q_measured = self.parse(measured)
        q_specified = self.parse(specified)
        
        if q_measured is None or q_specified is None:
            return False
            
        if allowed_margin.endswith('%'):
            try:
                margin_percent = float(allowed_margin.rstrip('%')) / 100.0
                if hasattr(q_specified, 'magnitude'):
                    # Pint quantity
                    diff = abs(q_measured - q_specified)
                    return diff <= (abs(q_specified) * margin_percent)
                else:
                    # Float fallback
                    return abs(q_measured - q_specified) <= (abs(q_specified) * margin_percent)
            except Exception:
                return False
        else:
            return self.compare_within_tolerance(measured, specified, allowed_margin)
