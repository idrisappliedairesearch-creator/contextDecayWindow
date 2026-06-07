import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.context_builder import build_prompt, estimate_tokens, _build_rule_block_text


class TestBuildPromptWithRules:
    def _make_rule_episodes(self):
        return [
            {
                "turn_number": 2,
                "user_message": "Always use bullet points",
                "assistant_message": "Understood, I will use bullet points.",
            }
        ]

    def _make_history_episodes(self):
        return [
            {
                "turn_number": 5,
                "user_message": "What is the capital of France?",
                "assistant_message": "The capital of France is Paris.",
            }
        ]

    def test_pinned_rules_block_present_with_rules(self):
        rule_eps = self._make_rule_episodes()
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", rule_eps)
        assert "--- PINNED RULES ---" in result
        assert "--- END PINNED RULES ---" in result

    def test_pinned_rules_before_history(self):
        rule_eps = self._make_rule_episodes()
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", rule_eps)
        rules_idx = result.index("--- PINNED RULES ---")
        history_idx = result.index("--- RETRIEVED CONVERSATION HISTORY ---")
        assert rules_idx < history_idx

    def test_rule_episode_content_visible(self):
        rule_eps = self._make_rule_episodes()
        result = build_prompt([], "System prompt", rule_eps)
        assert "[Turn 2]" in result
        assert "User: Always use bullet points" in result
        assert "Assistant: Understood, I will use bullet points." in result

    def test_no_rules_block_when_none(self):
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", None)
        assert "--- PINNED RULES ---" not in result

    def test_no_rules_block_when_empty(self):
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", [])
        assert "--- PINNED RULES ---" not in result

    def test_only_system_prompt_when_everything_empty(self):
        result = build_prompt([], "System prompt", None)
        assert result == "System prompt"

    def test_only_rules_no_history(self):
        rule_eps = self._make_rule_episodes()
        result = build_prompt([], "System prompt", rule_eps)
        assert "--- PINNED RULES ---" in result
        assert "--- RETRIEVED CONVERSATION HISTORY ---" not in result

    def test_rules_and_history_both_present(self):
        rule_eps = self._make_rule_episodes()
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", rule_eps)
        assert "--- PINNED RULES ---" in result
        assert "--- END PINNED RULES ---" in result
        assert "--- RETRIEVED CONVERSATION HISTORY ---" in result
        assert "--- END HISTORY ---" in result

    def test_multiple_rule_episodes(self):
        rule_eps = [
            {
                "turn_number": 1,
                "user_message": "Rule 1",
                "assistant_message": "OK 1",
            },
            {
                "turn_number": 3,
                "user_message": "Rule 2",
                "assistant_message": "OK 2",
            },
        ]
        result = build_prompt([], "System", rule_eps)
        assert "[Turn 1]" in result
        assert "[Turn 3]" in result
        assert "User: Rule 1" in result
        assert "User: Rule 2" in result

    def test_history_still_present_with_rules(self):
        rule_eps = self._make_rule_episodes()
        history_eps = self._make_history_episodes()
        result = build_prompt(history_eps, "System prompt", rule_eps)
        assert "What is the capital of France?" in result
        assert "The capital of France is Paris." in result


class TestBuildRuleBlockText:
    def test_returns_empty_string_for_none(self):
        assert _build_rule_block_text(None) == ""

    def test_returns_empty_string_for_empty_list(self):
        assert _build_rule_block_text([]) == ""

    def test_returns_formatted_block(self):
        rule_eps = [
            {
                "turn_number": 4,
                "user_message": "Use bold",
                "assistant_message": "Will do.",
            }
        ]
        text = _build_rule_block_text(rule_eps)
        assert "--- PINNED RULES ---" in text
        assert "[Turn 4]" in text
        assert "User: Use bold" in text
        assert "Assistant: Will do." in text
        assert "--- END PINNED RULES ---" in text


class TestRuleTokenEstimate:
    def test_estimate_tokens_on_rule_block(self):
        rule_eps = [
            {
                "turn_number": 1,
                "user_message": "Short rule",
                "assistant_message": "OK",
            }
        ]
        block = _build_rule_block_text(rule_eps)
        tokens = estimate_tokens(block)
        assert tokens == len(block) // 4
        assert isinstance(tokens, int)

    def test_estimate_zero_for_empty_block(self):
        tokens = estimate_tokens(_build_rule_block_text([]))
        assert tokens == 0
