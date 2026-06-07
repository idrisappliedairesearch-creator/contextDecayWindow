import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.rule_store import store_rule, get_all_rules
import uuid as uuid_mod
import numpy as np


class TestRuleStoreTable:
    def test_rule_store_table_created(self):
        db_path = tempfile.mktemp(suffix=".db")
        try:
            conn = init_db(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rule_store'"
            )
            assert cursor.fetchone() is not None
            conn.close()
        finally:
            if os.path.isfile(db_path):
                os.unlink(db_path)

    def test_rule_store_table_columns(self):
        db_path = tempfile.mktemp(suffix=".db")
        try:
            conn = init_db(db_path)
            cursor = conn.execute("PRAGMA table_info(rule_store)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            assert "id" in columns
            assert "episode_id" in columns
            assert "rule_summary" in columns
            assert "turn_number" in columns
            assert "created_at" in columns
            conn.close()
        finally:
            if os.path.isfile(db_path):
                os.unlink(db_path)

    def test_idempotent_with_rule_store(self):
        db_path = tempfile.mktemp(suffix=".db")
        try:
            conn1 = init_db(db_path)
            conn1.close()
            conn2 = init_db(db_path)
            cursor = conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert len(tables) == 4
            assert "rule_store" in tables
            conn2.close()
        finally:
            if os.path.isfile(db_path):
                os.unlink(db_path)


class TestStoreRule:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_valid_uuid(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "always use bullet points", "Yes, I will.", embedding, 1
            )
            rule_id = store_rule(self.conn, episode_id, "Always use bullet points", 1)
            uuid_mod.UUID(rule_id, version=4)
        finally:
            self._teardown_db()

    def test_writes_row_to_rule_store(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "always use bullet points", "Yes, I will.", embedding, 1
            )
            store_rule(self.conn, episode_id, "Always use bullet points", 1)
            cursor = self.conn.execute("SELECT COUNT(*) FROM rule_store")
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            self._teardown_db()

    def test_stores_correct_values(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "use markdown tables", "Will do.", embedding, 5
            )
            rule_id = store_rule(self.conn, episode_id, "Use markdown tables for data", 5)
            cursor = self.conn.execute(
                "SELECT episode_id, rule_summary, turn_number, created_at FROM rule_store WHERE id = ?",
                (rule_id,),
            )
            row = cursor.fetchone()
            assert row[0] == episode_id
            assert row[1] == "Use markdown tables for data"
            assert row[2] == 5
            assert row[3] is not None
        finally:
            self._teardown_db()

    def test_multiple_rules_accumulate(self):
        self._setup_db()
        try:
            embedding1 = np.zeros(1024, dtype=np.float32)
            ep1 = store_episode(self.conn, "rule 1", "ok", embedding1, 1)
            store_rule(self.conn, ep1, "Rule one", 1)

            embedding2 = np.zeros(1024, dtype=np.float32)
            ep2 = store_episode(self.conn, "rule 2", "ok", embedding2, 3)
            store_rule(self.conn, ep2, "Rule two", 3)

            cursor = self.conn.execute("SELECT COUNT(*) FROM rule_store")
            count = cursor.fetchone()[0]
            assert count == 2
        finally:
            self._teardown_db()


class TestGetAllRules:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_empty_list_when_no_rules(self):
        self._setup_db()
        try:
            rules = get_all_rules(self.conn)
            assert rules == []
        finally:
            self._teardown_db()

    def test_returns_all_rules(self):
        self._setup_db()
        try:
            embedding1 = np.zeros(1024, dtype=np.float32)
            ep1 = store_episode(self.conn, "rule 1", "ok", embedding1, 1)
            store_rule(self.conn, ep1, "Rule one", 1)

            embedding2 = np.ones(1024, dtype=np.float32)
            ep2 = store_episode(self.conn, "rule 2", "ok", embedding2, 5)
            store_rule(self.conn, ep2, "Rule two", 5)

            rules = get_all_rules(self.conn)
            assert len(rules) == 2
            assert rules[0]["rule_summary"] == "Rule one"
            assert rules[0]["turn_number"] == 1
            assert rules[1]["rule_summary"] == "Rule two"
            assert rules[1]["turn_number"] == 5
        finally:
            self._teardown_db()

    def test_returns_dicts_with_correct_keys(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            ep = store_episode(self.conn, "rule", "ok", embedding, 2)
            rule_id = store_rule(self.conn, ep, "Test rule", 2)
            rules = get_all_rules(self.conn)
            assert len(rules) == 1
            rule = rules[0]
            assert "id" in rule
            assert "episode_id" in rule
            assert "rule_summary" in rule
            assert "turn_number" in rule
            assert "created_at" in rule
            assert rule["id"] == rule_id
            assert rule["episode_id"] == ep
        finally:
            self._teardown_db()

    def test_ordered_by_turn_number(self):
        self._setup_db()
        try:
            embedding1 = np.zeros(1024, dtype=np.float32)
            ep1 = store_episode(self.conn, "rule 1", "ok", embedding1, 10)
            store_rule(self.conn, ep1, "Rule ten", 10)

            embedding2 = np.zeros(1024, dtype=np.float32)
            ep2 = store_episode(self.conn, "rule 2", "ok", embedding2, 3)
            store_rule(self.conn, ep2, "Rule three", 3)

            rules = get_all_rules(self.conn)
            assert rules[0]["turn_number"] == 3
            assert rules[1]["turn_number"] == 10
        finally:
            self._teardown_db()
