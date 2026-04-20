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
standards_seed — helper to (re)seed the GLOBAL standards DB from a JSON file.

Usage:
  python -m src.setup.standards_seed --json D:\path\to\standards.json
  # Optional:
  python -m src.setup.standards_seed --app-root D:\SerapeumAI --json D:\seed.json
"""

from __future__ import annotations

import argparse
import os
from typing import Optional, Sequence

from src.compliance.standards_db_initializer import ensure_global_db, seed_from_json


def _parse(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed global standards DB")
    p.add_argument("--app-root", default=os.getcwd(), help="Application root (holds .serapeum/global.sqlite3)")
    p.add_argument("--json", required=True, help="Path to seed JSON")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse(argv)
    db = ensure_global_db(args.app_root)
    if not os.path.isfile(args.json):
        raise SystemExit(f"Seed JSON not found: {args.json}")
    added = seed_from_json(args.json, app_root=args.app_root)
    print(f"[standards_seed] OK: db={db} added_rows={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
