import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from model_api_collector.config import ConfigError, load_settings
from model_api_collector.prompts import PromptError, load_prompt_cases
from model_api_collector.runner import _build_payload, run_evaluation


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="model-api-collector",
        description="Collect raw model responses directly through OneAPI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Check config and prompts")
    _add_input_arguments(validate)

    run = subparsers.add_parser("run", help="Run models against a prompt set")
    _add_input_arguments(run)
    run.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model aliases from YAML, or 'all'",
    )
    run.add_argument(
        "--repeat",
        type=int,
        default=2,
        help="Independent runs per model and prompt (default: 2)",
    )
    run.add_argument(
        "--delivery-mode",
        choices=("complete", "stream"),
        default=None,
        help="Override the model-configured delivery mode",
    )
    run.add_argument("--max-attempts", type=int, default=None)
    run.add_argument("--output", type=Path, default=Path("runs"))

    preflight = subparsers.add_parser(
        "preflight", help="Validate inputs and construct local request payloads"
    )
    _add_input_arguments(preflight)
    preflight.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model aliases from YAML, or 'all'",
    )
    preflight.add_argument(
        "--delivery-mode",
        choices=("complete", "stream"),
        default=None,
    )
    return parser


def _add_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))


def _resolve_models(requested: Sequence[str], available: Sequence[str]) -> List[str]:
    if requested == ["all"]:
        return list(available)
    if "all" in requested:
        raise ConfigError("'all' cannot be combined with named models")
    unknown = [alias for alias in requested if alias not in available]
    if unknown:
        raise ConfigError(f"Unknown model alias: {', '.join(unknown)}")
    return list(requested)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.config, env_file=args.env_file)
        prompt_cases = load_prompt_cases(args.prompts)
        if args.command == "validate":
            print("Configuration valid")
            print(f"Models: {len(settings.models)}")
            print(f"Prompts: {len(prompt_cases)}")
            return 0

        model_aliases = _resolve_models(args.models, list(settings.models))
        if args.command == "preflight":
            for alias in model_aliases:
                _build_payload(
                    settings.models[alias],
                    prompt_cases[0],
                    delivery_mode=args.delivery_mode,
                )
            print("Preflight valid")
            print(f"Models: {len(model_aliases)}")
            print(f"Prompts: {len(prompt_cases)}")
            print(f"Delivery mode: {args.delivery_mode or 'model-configured'}")
            print("Requests: 0")
            return 0

        summary = run_evaluation(
            settings=settings,
            model_aliases=model_aliases,
            prompt_cases=prompt_cases,
            repeat=args.repeat,
            output_root=args.output,
            config_sha256=_sha256_file(args.config),
            prompts_sha256=_sha256_file(args.prompts),
            delivery_mode=args.delivery_mode,
            max_attempts=args.max_attempts,
        )
    except (ConfigError, PromptError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Run: {summary.run_id}")
    print(f"Requests: {summary.total}")
    print(f"Completed: {summary.successful}")
    print(f"Failed: {summary.failed}")
    print(f"Results: {summary.run_path.resolve()}")
    return 1 if summary.failed else 0
