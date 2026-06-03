def build_prompt(episodes: list, system_prompt: str) -> str:
    if not episodes:
        return system_prompt

    parts = [system_prompt, ""]
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
