# Benchmarks

This directory stores benchmark prompts, gold answers, and program results in
separate JSONL files for easy comparison and scoring.

## Layout

- `benchmarks/queries/` - text-only prompts (one JSONL file per collection).
- `benchmarks/answers/` - gold answers keyed by `id`.
- `benchmarks/results/` - per-program, per-run outputs with scoring + notes.

## JSONL schemas

### Query records

```json
{"id":"string","question":"string","tags":["string"]}
```

### Answer records

```json
{"id":"string","answer":{}}
```

### Result records

```json
{
  "id": "string",
  "program": "string",
  "run_id": "string",
  "response": {},
  "notes": "string",
  "calc": {},
  "score": {},
  "latency_ms": 0
}
```

Notes:
- `id` must match a record in `benchmarks/queries/` and `benchmarks/answers/`.
- `response` is what the program produced.
- `calc` captures how the response was computed (e.g., endpoints + payloads).
- `score` is a free-form object for evaluation metrics.
