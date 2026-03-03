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
standards_db.py — Global Standards Database
-------------------------------------------
Manages the offline SQLite database for AECO standards.
"""

import sqlite3
import os
from typing import List, Dict, Any

class StandardsDatabase:
    def __init__(self, db_path: str = ".serapeum/standards.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Standards metadata
        c.execute("""
            CREATE TABLE IF NOT EXISTS standards (
                id TEXT PRIMARY KEY,
                code TEXT,
                name TEXT,
                version TEXT,
                region TEXT,
                discipline TEXT,
                source_url TEXT
            )
        """)
        
        # Clauses
        c.execute("""
            CREATE TABLE IF NOT EXISTS clauses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                standard_id TEXT,
                clause_id TEXT,
                section TEXT,
                title TEXT,
                text TEXT,
                tags TEXT,
                FOREIGN KEY(standard_id) REFERENCES standards(id)
            )
        """)
        
        # FTS5 for full-text search
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS clauses_fts USING fts5(text, title, content='clauses', content_rowid='id')")
        
        # Triggers to keep FTS updated
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS clauses_ai AFTER INSERT ON clauses BEGIN
              INSERT INTO clauses_fts(rowid, text, title) VALUES (new.id, new.text, new.title);
            END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS clauses_ad AFTER DELETE ON clauses BEGIN
              INSERT INTO clauses_fts(clauses_fts, rowid, text, title) VALUES('delete', old.id, old.text, old.title);
            END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS clauses_au AFTER UPDATE ON clauses BEGIN
              INSERT INTO clauses_fts(clauses_fts, rowid, text, title) VALUES('delete', old.id, old.text, old.title);
              INSERT INTO clauses_fts(rowid, text, title) VALUES (new.id, new.text, new.title);
            END;
        """)

        conn.commit()
        conn.close()

    def ingest_standard(self, meta: Dict[str, Any], clauses: List[Dict[str, Any]]):
        """
        Ingest a full standard with its clauses.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO standards (id, code, name, version, region, discipline, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                meta["id"], meta.get("code"), meta.get("name"), meta.get("version"),
                meta.get("region"), meta.get("discipline"), meta.get("source_url")
            ))
            
            for cl in clauses:
                c.execute("""
                    INSERT INTO clauses (standard_id, clause_id, section, title, text, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    meta["id"], cl.get("clause_id"), cl.get("section"), 
                    cl.get("title"), cl.get("text"), cl.get("tags")
                ))
            
            conn.commit()
        finally:
            conn.close()

    def search_clauses(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Full-text search for clauses.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Simple FTS search
        rows = c.execute("""
            SELECT c.*, s.code as std_code, s.name as std_name 
            FROM clauses c
            JOIN standards s ON c.standard_id = s.id
            WHERE c.id IN (SELECT rowid FROM clauses_fts WHERE clauses_fts MATCH ? ORDER BY rank)
            LIMIT ?
        """, (query, limit)).fetchall()
        
        conn.close()
        return [dict(r) for r in rows]

    def get_all_clauses(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT c.*, s.code as std_code 
            FROM clauses c 
            JOIN standards s ON c.standard_id = s.id 
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get schema information for introspection.
        Returns table names, columns, and row counts.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        info = {"tables": {}}
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "not_null": bool(col["notnull"]),
                    "pk": bool(col["pk"])
                }
                for col in cursor.fetchall()
            ]
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                row_count = cursor.fetchone()["cnt"]
            except Exception as e:
                print(f"[WARN] Could not get row count for table {table}: {e}")
                row_count = 0
            
            info["tables"][table] = {
                "columns": columns,
                "row_count": row_count
            }
        
        conn.close()
        return info
    
    def bulk_ingest_clauses(self, standard_id: str, clauses: List[Dict[str, Any]]) -> int:
        """
        Efficiently ingest multiple clauses for a standard.
        
        Args:
            standard_id: ID of the parent standard
            clauses: List of clause dictionaries with keys:
                     clause_id, section, title, text, tags (optional)
        
        Returns:
            Number of clauses inserted
        """
        if not clauses:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Batch insert
            clause_tuples = [
                (
                    standard_id,
                    cl.get("clause_id", ""),
                    cl.get("section", ""),
                    cl.get("title", ""),
                    cl.get("text", ""),
                    cl.get("tags", "")
                )
                for cl in clauses
            ]
            
            c.executemany(
                """
                INSERT INTO clauses (standard_id, clause_id, section, title, text, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                clause_tuples
            )
            
            conn.commit()
            inserted = c.rowcount
            
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Bulk ingest failed: {e}")
            inserted = 0
        finally:
            conn.close()
        
        return inserted
