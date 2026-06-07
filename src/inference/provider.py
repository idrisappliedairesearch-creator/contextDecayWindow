import json
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

from llama_cpp import Llama, llama_cpp


RULE_DETECTION_INSTRUCTION = """\
After your response, append exactly one line in this format and no other text:
<rule_detection>{"contains_rule": BOOL, "rule_summary": "SUMMARY_OR_NULL"}</rule_detection>

Set contains_rule to true if and only if the user's message establishes a
persistent behavioral rule, formatting requirement, or constraint that should
apply to all future responses. Set rule_summary to a concise description of the
rule if contains_rule is true, otherwise null."""

RULE_DETECTION_PATTERN = r"<rule_detection>(.*?)</rule_detection>"


@dataclass
class InferenceResult:
    assistant_message: str
    tokens_per_second: float
    time_to_first_token: float
    output_tokens: int
    contains_rule: bool = False
    rule_summary: Optional[str] = None


class InferenceProvider:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        model_path = os.environ.get("CDW_INFERENCE_MODEL_PATH")
        if not model_path:
            raise EnvironmentError(
                "CDW_INFERENCE_MODEL_PATH environment variable is not set. "
                "Set it to the absolute path of your Qwen3.6 27B Q6_K GGUF file."
            )

        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Inference model not found at: {model_path}"
            )

        n_gpu_layers = int(os.environ.get("CDW_INFERENCE_N_GPU_LAYERS", "-1"))
        n_ctx = int(os.environ.get("CDW_INFERENCE_N_CTX", "32768"))

        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
            type_k=llama_cpp.GGML_TYPE_Q8_0,
            type_v=llama_cpp.GGML_TYPE_Q8_0,
            flash_attn=llama_cpp.LLAMA_FLASH_ATTN_TYPE_ENABLED,
        )
        self._initialized = True

    def complete(self, prompt: str, suppress_rule_detection: bool = False) -> InferenceResult:
        augmented_prompt = self._inject_rule_detection(prompt)

        start = time.perf_counter()
        response = self._llm(
            augmented_prompt,
            max_tokens=1024,
            echo=False,
            stream=False,
        )
        elapsed = time.perf_counter() - start

        raw_message = response["choices"][0]["text"]
        output_tokens = response["usage"]["completion_tokens"]
        tokens_per_second = output_tokens / elapsed if elapsed > 0 else 0.0
        time_to_first_token = elapsed / output_tokens if output_tokens > 0 else elapsed

        if suppress_rule_detection:
            assistant_message = raw_message.strip()
            contains_rule = False
            rule_summary = None
        else:
            assistant_message, contains_rule, rule_summary = self._parse_rule_detection(raw_message)

        return InferenceResult(
            assistant_message=assistant_message,
            tokens_per_second=tokens_per_second,
            time_to_first_token=time_to_first_token,
            output_tokens=output_tokens,
            contains_rule=contains_rule,
            rule_summary=rule_summary,
        )

    def _inject_rule_detection(self, prompt: str) -> str:
        if RULE_DETECTION_INSTRUCTION in prompt:
            return prompt
        return f"{prompt}\n\n{RULE_DETECTION_INSTRUCTION}"

    def _parse_rule_detection(self, raw_output: str) -> tuple[str, bool, Optional[str]]:
        match = re.search(RULE_DETECTION_PATTERN, raw_output, re.DOTALL)

        if not match:
            clean = raw_output.strip()
            return clean, False, None

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
