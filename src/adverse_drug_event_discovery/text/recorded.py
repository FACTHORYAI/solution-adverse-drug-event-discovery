"""A TextModel that replays recorded answers, so runs and tests need no network."""

from __future__ import annotations

from typing import Any


class RecordedTextModel:
    """Answer from recorded answers, keyed by task and text.

    The answers map has the shape {"<task>": {"<text>": "<model answer>"}}; the
    task comes from the `task:` line on the prompt, so the same text can have
    separate answers for different prompts. Decode the JSON with io.read_json.
    """

    def __init__(self, answers: dict[str, dict[str, str]]) -> None:
        self._answers = answers

    def complete(self, instructions: str, text: str) -> str:
        """Return the recorded answer for one task and text."""
        task = _task_of(instructions)
        task_answers = self._answers.get(task)
        if task_answers is None:
            message = f"No recorded answers for task {task!r}"
            raise KeyError(message)
        answer = task_answers.get(text)
        if answer is None:
            message = f"No recorded {task!r} answer for text {text[:60]!r}"
            raise KeyError(message)
        return answer


def load_answers(answers: Any) -> dict[str, dict[str, str]]:
    """Check the shape of decoded recorded answers and return them."""
    if not isinstance(answers, dict) or not all(
        isinstance(task, dict) for task in answers.values()
    ):
        message = "Recorded answers must map task names to {text: answer}"
        raise ValueError(message)
    return answers


def _task_of(instructions: str) -> str:
    first_line = instructions.splitlines()[0] if instructions else ""
    if first_line.startswith("task:"):
        return first_line.removeprefix("task:").strip()
    message = "Prompt must start with a `task: <name>` line"
    raise ValueError(message)
