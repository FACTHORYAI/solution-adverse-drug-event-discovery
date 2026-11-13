"""The command line: one sub-command per job."""

from __future__ import annotations

import argparse
import logging
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.config import Settings, load_settings
from adverse_drug_event_discovery.jobs import REGISTRY, JobSpec, call_run, param_values
from adverse_drug_event_discovery.text.recorded import RecordedTextModel, load_answers

logger = logging.getLogger(__name__)

_TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool}


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, run one job on the sample data and write its outputs."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)
    spec: JobSpec = args.job_spec
    settings = load_settings()
    inputs = {name: io.read_table(name, settings) for name in spec.inputs}
    model = _model_from_args(args, settings) if spec.needs_model else None
    outputs = call_run(spec, inputs, param_values(spec, args), model)
    for name, table in outputs.items():
        io.write_table(name, table, settings)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adverse_drug_event_discovery",
        description=(
            "Find adverse drug events and the drugs they follow in conversational text, "
            "and analyse them as tables."
        ),
    )
    subparsers = parser.add_subparsers(dest="job", required=True)
    for name, spec in REGISTRY.items():
        sub = subparsers.add_parser(name, help=spec.description)
        _add_params(sub, spec.params_cls)
        if spec.needs_model:
            sub.add_argument(
                "--model-answers",
                default=None,
                help="Path to a recorded-answers JSON file (see text.interface).",
            )
        sub.set_defaults(job_spec=spec)
    return parser


def _add_params(sub: argparse.ArgumentParser, params_cls: type) -> None:
    for field in fields(params_cls):
        flag = f"--{field.name.replace('_', '-')}"
        argument_type = _TYPE_MAP.get(str(field.type), str)
        if argument_type is bool:
            sub.add_argument(
                flag, dest=field.name, action=argparse.BooleanOptionalAction, default=field.default
            )
            continue
        options: dict[str, Any] = {"type": argument_type, "dest": field.name}
        if field.default is MISSING:
            options["required"] = True
        else:
            options["default"] = field.default
        sub.add_argument(flag, **options)


def _model_from_args(args: argparse.Namespace, settings: Settings) -> RecordedTextModel:
    path = (
        args.model_answers if getattr(args, "model_answers", None) else settings.model_answers_path
    )
    if path is None:
        message = (
            "This job needs a TextModel; pass --model-answers with a recorded-answers JSON file "
            "or plug a provider in behind adverse_drug_event_discovery.text.interface"
        )
        raise SystemExit(message)
    return RecordedTextModel(load_answers(io.read_json(Path(path))))
