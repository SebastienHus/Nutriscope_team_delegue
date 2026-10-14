"""Résultat commun des étapes et exécution journalisée."""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field

from nutriscope import journal
from nutriscope.files import StepError


@dataclass
class StepResult:
    step: str
    status: str = "ok"                    # ok | skipped | failed
    rows: int | None = None
    outputs: list[str] = field(default_factory=list)
    message: str = ""
    seconds: float = 0.0


def run_step(name: str, func, settings, force: bool = False, verbose: bool = False) -> StepResult:
    """Exécute une étape, mesure sa durée, transforme toute erreur en résultat `failed`, journalise."""
    start = time.perf_counter()
    try:
        result = func(settings, force=force)
    except StepError as error:
        result = StepResult(name, "failed", message=str(error))
    except Exception as error:  # erreur imprévue : on la journalise quand même (sinon le journal ment)
        result = StepResult(name, "failed", message=f"{error.__class__.__name__}: {error}")
        if verbose:
            traceback.print_exc()
    result.step = name
    result.seconds = time.perf_counter() - start
    journal.append(settings, result)
    return result


def skipped(name: str, settings, message: str) -> StepResult:
    result = StepResult(name, "skipped", message=message)
    journal.append(settings, result)
    return result
