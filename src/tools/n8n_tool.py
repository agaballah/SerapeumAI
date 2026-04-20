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

import json
import urllib.request
import urllib.error
from typing import Any, Dict
from src.tools.base_tool import BaseTool

class N8NTool(BaseTool):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "n8n_workflow"

    @property
    def description(self) -> str:
        return "Triggers an external n8n workflow for complex processing or data retrieval. Sends JSON payload."

    def execute(self, payload: Dict[str, Any]) -> str:
        if not self.webhook_url:
            return "Error: n8n Webhook URL is not configured."

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url, 
                data=data, 
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                resp_data = response.read().decode('utf-8')
                return f"Workflow Response: {resp_data}"
                
        except urllib.error.HTTPError as e:
            return f"Workflow Error (HTTP {e.code}): {e.reason}"
        except Exception as e:
            return f"Workflow Connection Error: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": "JSON payload to send to the workflow. Structure depends on the specific workflow requirements."
                }
            },
            "required": ["payload"]
        }
