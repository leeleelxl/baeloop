from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from baeloop.models import AgentConfig, RunRecord, TaskSet

T = TypeVar("T", bound=BaseModel)


def read_jsonl_records(path: Path) -> list[RunRecord]:
    records: list[RunRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(RunRecord.model_validate_json(stripped))
            except ValueError as exc:
                raise ValueError(f"Invalid JSONL record at {path}:{line_number}") from exc
    return records


def write_jsonl_records(path: Path, records: list[RunRecord]) -> None:
    reset_jsonl_records(path)
    for record in records:
        append_jsonl_record(path, record)


def reset_jsonl_records(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def append_jsonl_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def write_json(path: Path, payload: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_model_json(path: Path, model: type[T]) -> T:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def read_json_dict(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml_dict(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def read_agent_config(path: Path) -> AgentConfig:
    return AgentConfig.model_validate(read_yaml_dict(path))


def read_taskset(path: Path) -> TaskSet:
    return TaskSet.model_validate(read_yaml_dict(path))


def write_yaml_dict(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
