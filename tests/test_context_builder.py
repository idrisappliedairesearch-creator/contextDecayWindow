import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.context_builder import build_prompt, estimate_tokens


class TestBuildPrompt:
    def test_empty_episodes_returns_system_prompt(self):
        result = build_prompt([], "You are an assistant.")
        assert result == "You are an assistant."

    def test_single_episode_format(self):
        episodes = [
            {
                "id": "ep1",
                "turn_number": 1,
                "user_message": "Hello",
                "assistant_message": "Hi there!",
            }
        ]
        result = build_prompt(episodes, "System prompt here.")
        assert "System prompt here." in result
        assert "--- RETRIEVED CONVERSATION HISTORY ---" in result
        assert "[Turn 1]" in result
        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result
        assert "--- END HISTORY ---" in result

    def test_multiple_episodes_preserve_order(self):
        episodes = [
            {
                "id": "ep1",
                "turn_number": 1,
                "user_message": "First",
                "assistant_message": "Response 1",
            },
            {
                "id": "ep2",
                "turn_number": 2,
                "user_message": "Second",
                "assistant_message": "Response 2",
            },
        ]
        result = build_prompt(episodes, "Sys")
        idx1 = result.index("[Turn 1]")
        idx2 = result.index("[Turn 2]")
        assert idx1 < idx2

    def test_turn_numbers_visible(self):
        episodes = [
            {
                "id": "ep1",
                "turn_number": 5,
                "user_message": "Q",
                "assistant_message": "A",
            },
        ]
        result = build_prompt(episodes, "S")
        assert "[Turn 5]" in result

    def test_does_not_include_current_user_message(self):
        episodes = [
            {
                "id": "ep1",
                "turn_number": 1,
                "user_message": "Past question",
                "assistant_message": "Past answer",
            },
        ]
        result = build_prompt(episodes, "Sys")
        assert "Past question" in result
        assert "Past answer" in result

    def test_empty_user_or_assistant_message(self):
        episodes = [
            {
                "id": "ep1",
                "turn_number": 1,
                "user_message": "",
                "assistant_message": "",
            }
        ]
        result = build_prompt(episodes, "Sys")
        assert "User: " in result
        assert "Assistant: " in result


class TestEstimateTokens:
    def test_basic_estimation(self):
        text = "Hello, world!"
        result = estimate_tokens(text)
        assert result == len(text) // 4

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_known_length(self):
        text = "a" * 100
        assert estimate_tokens(text) == 25

    def test_odd_length(self):
        text = "abc"
        assert estimate_tokens(text) == 0

    def test_larger_text(self):
        text = "This is a longer piece of text that should produce a reasonable token estimate."
        result = estimate_tokens(text)
        assert result == len(text) // 4
        assert isinstance(result, int)
