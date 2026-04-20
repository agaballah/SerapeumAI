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

import math
from typing import Any, Dict
from src.tools.base_tool import BaseTool

class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Useful for performing mathematical calculations. Input should be a valid mathematical expression string."

    def execute(self, expression: str) -> str:
        """
        Safely evaluates a mathematical expression.
        """
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
        
        try:
            # Compile the expression to bytecode
            code = compile(expression, "<string>", "eval")
            
            # Check for unsafe operations (like attribute access or function calls to non-allowed functions)
            for name in code.co_names:
                if name not in allowed_names:
                    raise ValueError(f"Use of '{name}' is not allowed")
            
            # Evaluate
            result = eval(code, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16) * 5')"
                }
            },
            "required": ["expression"]
        }
