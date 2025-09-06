#!/usr/bin/env python3
from openai import OpenAI
import json

client = OpenAI()

schema = {
    "name": "ModelComparison",
    "schema": {
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model_name", "summary"],
    },
}

models = ["gpt-4.1", "gpt-5"]


def run_model(model_id: str):
    kwargs = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict JSON generator. No extra text.",
            },
            {
                "role": "user",
                "content": f"Return a profile of {model_id} with strengths and weaknesses.",
            },
        ],
        "response_format": {"type": "json_schema", "json_schema": schema},
    }

    # GPT-5 rejects non-default temperature
    if not model_id.startswith("gpt-5"):
        kwargs["temperature"] = 0

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def main():
    results = {}
    for m in models:
        try:
            raw = run_model(m)
            parsed = json.loads(raw)
            results[m] = parsed
        except Exception as e:
            results[m] = {"error": str(e)}

    print("\n=== Model Comparison ===\n")
    for m, data in results.items():
        print(f"--- {m} ---")
        print(json.dumps(data, indent=2))
        print()


if __name__ == "__main__":
    main()
