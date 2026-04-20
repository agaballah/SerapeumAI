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

# expose panels subpackage
from .visualization_panel import VisualizationPanel
# If you added these later, leave them imported too:
try:
    from .analysis_panel import AnalysisPanel  # optional
except Exception:
    pass
try:
    from .compliance_panel import CompliancePanel  # optional
except Exception:
    pass

__all__ = ["VisualizationPanel", "AnalysisPanel", "CompliancePanel"]
