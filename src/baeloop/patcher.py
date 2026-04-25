from __future__ import annotations

from copy import deepcopy
from typing import Any

from baeloop.models import AdvisorProposal, AgentConfig

ALLOWED_PATCH_KEYS = {
    "max_steps",
    "retry_policy",
    "observation_mode",
    "prompt_version",
    "no_op_policy",
}


def materialize_config_patch(
    base_config: dict[str, Any],
    proposal: AdvisorProposal,
) -> dict[str, Any]:
    unknown_keys = set(proposal.patch) - ALLOWED_PATCH_KEYS
    if unknown_keys:
        raise ValueError(f"Unsupported patch keys: {sorted(unknown_keys)}")

    patched = _deep_merge(deepcopy(base_config), proposal.patch)
    if proposal.patch and not _patch_changes_value(base_config, patched, proposal.patch):
        raise ValueError("Advisor patch does not change the base config")

    base_id = str(base_config.get("id", "base"))
    patched["id"] = f"{base_id}_{proposal.hypothesis_id}"
    patched["parent_config_id"] = base_id
    patched["advisor_hypothesis_id"] = proposal.hypothesis_id
    AgentConfig.model_validate(patched)
    return patched


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def _patch_changes_value(
    base: dict[str, Any],
    patched: dict[str, Any],
    patch: dict[str, Any],
) -> bool:
    for key, value in patch.items():
        if (
            isinstance(value, dict)
            and isinstance(base.get(key), dict)
            and isinstance(patched.get(key), dict)
        ):
            if _patch_changes_value(base[key], patched[key], value):
                return True
            continue
        if base.get(key) != patched.get(key):
            return True
    return False
