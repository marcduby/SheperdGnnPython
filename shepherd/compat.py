from __future__ import annotations

from pathlib import Path
from typing import Any

import torch


def resolve_runtime_device(n_gpus: int | None = None) -> torch.device:
    if n_gpus and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def trainer_accelerator_kwargs(n_gpus: int | None = None) -> dict[str, Any]:
    if n_gpus and torch.cuda.is_available():
        return {"accelerator": "gpu", "devices": n_gpus}
    return {"accelerator": "cpu", "devices": 1}


def resolve_project_path(value: str | Path | None, base_dir: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else base_dir / path
