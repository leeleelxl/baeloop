from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from baeloop.models import DependencyProbe, EnvironmentReport

AGENTLAB_MODULES = [
    "agentlab",
    "browsergym",
    "browsergym.miniwob",
    "gymnasium",
    "playwright",
]


def probe_modules(modules: list[str], strict_import: bool = True) -> list[DependencyProbe]:
    probes: list[DependencyProbe] = []
    for module in modules:
        if strict_import:
            probes.append(_probe_module_import(module))
        else:
            probes.append(_probe_module_spec(module))
    return probes


def probe_playwright_chromium(sync_playwright_factory: Any | None = None) -> DependencyProbe:
    if sync_playwright_factory is None:
        try:
            sync_playwright_factory = import_module("playwright.sync_api").sync_playwright
        except Exception as exc:
            return DependencyProbe(
                module="playwright.chromium",
                available=False,
                note=f"playwright import failed: {type(exc).__name__}: {exc}",
            )

    try:
        with sync_playwright_factory() as playwright:
            executable_path = Path(playwright.chromium.executable_path)
    except Exception as exc:
        return DependencyProbe(
            module="playwright.chromium",
            available=False,
            note=f"browser probe failed: {type(exc).__name__}: {exc}",
        )

    if executable_path.exists():
        return DependencyProbe(
            module="playwright.chromium",
            available=True,
            note=str(executable_path),
        )
    return DependencyProbe(
        module="playwright.chromium",
        available=False,
        note=f"chromium executable not found at {executable_path}; run `playwright install chromium`",
    )


def probe_miniwob_url(miniwob_url: str | None = None) -> DependencyProbe:
    resolved_url = miniwob_url or os.environ.get("MINIWOB_URL")
    if not resolved_url:
        return DependencyProbe(
            module="MINIWOB_URL",
            available=False,
            note="environment variable is not set",
        )

    parsed = urlparse(resolved_url)
    if parsed.scheme != "file":
        return DependencyProbe(
            module="MINIWOB_URL",
            available=True,
            note=resolved_url,
        )

    path = Path(parsed.path)
    if path.exists():
        return DependencyProbe(
            module="MINIWOB_URL",
            available=True,
            note=resolved_url,
        )
    return DependencyProbe(
        module="MINIWOB_URL",
        available=False,
        note=f"file URL path does not exist: {path}",
    )


def probe_agentlab_environment(
    strict_import: bool = True,
    check_playwright_browser: bool = True,
    check_miniwob_url: bool = True,
) -> EnvironmentReport:
    dependencies = probe_modules(AGENTLAB_MODULES, strict_import=strict_import)
    if check_playwright_browser:
        dependencies.append(probe_playwright_chromium())
    if check_miniwob_url:
        dependencies.append(probe_miniwob_url())
    return EnvironmentReport(
        adapter="agentlab",
        ready=all(dependency.available for dependency in dependencies),
        dependencies=dependencies,
    )


def _probe_module_import(module: str) -> DependencyProbe:
    try:
        import_module(module)
    except Exception as exc:
        return DependencyProbe(
            module=module,
            available=False,
            note=f"import failed: {type(exc).__name__}: {exc}",
        )
    return DependencyProbe(module=module, available=True)


def _probe_module_spec(module: str) -> DependencyProbe:
    try:
        available = find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError) as exc:
        return DependencyProbe(
            module=module,
            available=False,
            note=f"spec probe failed: {type(exc).__name__}: {exc}",
        )
    if available:
        return DependencyProbe(module=module, available=True)
    return DependencyProbe(
        module=module,
        available=False,
        note="module import spec not found",
    )
