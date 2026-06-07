def build_prompt(
    episodes: list,
    system_prompt: str,
    rule_episodes: list = None,
) -> str:
    parts = [system_prompt, ""]

    if rule_episodes:
        parts.append("--- PINNED RULES ---")
        for ep in rule_episodes:
            parts.append(f"[Turn {ep['turn_number']}]")
            parts.append(f"User: {ep['user_message']}")
            parts.append(f"Assistant: {ep['assistant_message']}")
            parts.append("")
        parts.append("--- END PINNED RULES ---")
        parts.append("")

    if not episodes and not rule_episodes:
        return system_prompt

    if episodes:
        parts.append("--- RETRIEVED CONVERSATION HISTORY ---")

        for ep in episodes:
            parts.append(f"[Turn {ep['turn_number']}]")
            parts.append(f"User: {ep['user_message']}")
            parts.append(f"Assistant: {ep['assistant_message']}")
            parts.append("")

        parts.append("--- END HISTORY ---")

    return "\n".join(parts)


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def _build_rule_block_text(rule_episodes: list) -> str:
    if not rule_episodes:
        return ""
    lines = ["--- PINNED RULES ---"]
    for ep in rule_episodes:
        lines.append(f"[Turn {ep['turn_number']}]")
        lines.append(f"User: {ep['user_message']}")
        lines.append(f"Assistant: {ep['assistant_message']}")
        lines.append("")
    lines.append("--- END PINNED RULES ---")
    return "\n".join(lines)
