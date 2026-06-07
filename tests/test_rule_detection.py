import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.inference.provider import InferenceResult, RULE_DETECTION_INSTRUCTION, RULE_DETECTION_PATTERN


class TestInferenceResultFields:
    def test_new_fields_exist(self):
        result = InferenceResult(
            assistant_message="Hello",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
            contains_rule=True,
            rule_summary="Always be polite",
        )
        assert result.contains_rule is True
        assert result.rule_summary == "Always be polite"

    def test_defaults_are_safe(self):
        result = InferenceResult(
            assistant_message="Hello",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
        )
        assert result.contains_rule is False
        assert result.rule_summary is None

    def test_contains_rule_false_with_none_summary(self):
        result = InferenceResult(
            assistant_message="Hello",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
            contains_rule=False,
            rule_summary=None,
        )
        assert result.contains_rule is False
        assert result.rule_summary is None


class TestRuleDetectionTagParsing:
    def _parse_tag(self, raw_output: str) -> tuple:
        import re
        match = re.search(RULE_DETECTION_PATTERN, raw_output, re.DOTALL)

        if not match:
            return raw_output.strip(), False, None

        json_str = match.group(1).strip()
        clean_message = raw_output[:match.start()] + raw_output[match.end():]
        clean_message = clean_message.strip()

        try:
            data = json.loads(json_str)
            contains_rule = bool(data.get("contains_rule", False))
            rule_summary = data.get("rule_summary") if contains_rule else None
            return clean_message, contains_rule, rule_summary
        except (json.JSONDecodeError, TypeError):
            return clean_message, False, None

    def test_valid_tag_true_parsed(self):
        raw = 'Here is my response.\n<rule_detection>{"contains_rule": true, "rule_summary": "Use bullet points"}</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert message == "Here is my response."
        assert contains is True
        assert summary == "Use bullet points"

    def test_valid_tag_false_parsed(self):
        raw = 'Just a normal response.\n<rule_detection>{"contains_rule": false, "rule_summary": null}</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert message == "Just a normal response."
        assert contains is False
        assert summary is None

    def test_tag_stripped_from_message(self):
        raw = 'The answer is 42.<rule_detection>{"contains_rule": true, "rule_summary": "Always answer with 42"}</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert "<rule_detection>" not in message
        assert "</rule_detection>" not in message
        assert contains is True

    def test_no_tag_defaults_safe(self):
        raw = "Just a normal response without any tag."
        message, contains, summary = self._parse_tag(raw)
        assert message == "Just a normal response without any tag."
        assert contains is False
        assert summary is None

    def test_malformed_json_defaults_safe(self):
        raw = 'Some text<rule_detection>{not valid json}</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert message == "Some text"
        assert contains is False
        assert summary is None

    def test_malformed_partial_json(self):
        raw = 'Text<rule_detection>{"contains_rule": true, "rule_summary": "incomplete</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert contains is False
        assert summary is None

    def test_tag_with_leading_trailing_whitespace(self):
        raw = '  Response text  \n<rule_detection>{"contains_rule": true, "rule_summary": "Be concise"}</rule_detection>  '
        message, contains, summary = self._parse_tag(raw)
        assert message == "Response text"
        assert contains is True
        assert summary == "Be concise"

    def test_multiline_tag_content(self):
        raw = 'Response\n<rule_detection>\n{"contains_rule": true, "rule_summary": "Multiline test"}\n</rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert message == "Response"
        assert contains is True
        assert summary == "Multiline test"

    def test_empty_tag_content(self):
        raw = 'Response<rule_detection></rule_detection>'
        message, contains, summary = self._parse_tag(raw)
        assert message == "Response"
        assert contains is False
        assert summary is None

    def test_tag_in_middle_of_response(self):
        raw = 'Start of response<rule_detection>{"contains_rule": true, "rule_summary": "Mid tag"}</rule_detection> end part'
        message, contains, summary = self._parse_tag(raw)
        assert "Start of response" in message
        assert "end part" in message
        assert contains is True
        assert summary == "Mid tag"


class TestRuleDetectionInstruction:
    def test_instruction_is_non_empty(self):
        assert len(RULE_DETECTION_INSTRUCTION) > 0
        assert "rule_detection" in RULE_DETECTION_INSTRUCTION

    def test_instruction_mentions_contains_rule(self):
        assert "contains_rule" in RULE_DETECTION_INSTRUCTION

    def test_instruction_mentions_rule_summary(self):
        assert "rule_summary" in RULE_DETECTION_INSTRUCTION


class TestRuleDetectionPattern:
    def test_pattern_matches_standard_tag(self):
        import re
        text = '<rule_detection>{"contains_rule": true, "rule_summary": "test"}</rule_detection>'
        match = re.search(RULE_DETECTION_PATTERN, text, re.DOTALL)
        assert match is not None
        assert '"contains_rule": true' in match.group(1)

    def test_pattern_does_not_match_without_tag(self):
        import re
        text = "Normal response with no tag."
        match = re.search(RULE_DETECTION_PATTERN, text, re.DOTALL)
        assert match is None
