import json

import pytest

from model_api_collector.prompts import PromptError, load_prompt_cases


def test_load_prompt_cases_preserves_messages_exactly(tmp_path):
    path = tmp_path / "prompts.jsonl"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        }
    ]
    path.write_text(
        json.dumps(
            {
                "id": "vision-001",
                "title": "Image description",
                "messages": messages,
                "tags": ["vision"],
                "notes": "Keep original input",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    cases = load_prompt_cases(path)

    assert cases[0].id == "vision-001"
    assert cases[0].messages == messages
    assert cases[0].tags == ["vision"]
    assert cases[0].notes == "Keep original input"
    assert "system" not in [message["role"] for message in cases[0].messages]


@pytest.mark.parametrize(
    "lines, message",
    [
        (['{"id":"a","messages":[{"role":"user","content":"x"}]}', '{"id":"a","messages":[{"role":"user","content":"y"}]}'], "duplicate"),
        (["not-json"], "line 1"),
        (['{"id":"a"}'], "messages"),
        (['{"id":"a","messages":[]}'], "non-empty"),
        (['{"id":"a","messages":[{"content":"x"}]}'], "role"),
        (['{"id":"a","messages":[{"role":"user"}]}'], "content"),
    ],
)
def test_load_prompt_cases_rejects_invalid_rows(tmp_path, lines, message):
    path = tmp_path / "prompts.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(PromptError, match=message):
        load_prompt_cases(path)
