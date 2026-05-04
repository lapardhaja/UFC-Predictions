"""Optuna hyperparameter search — run manually when enough data exists."""

from __future__ import annotations

import argparse

try:
    import optuna
except ImportError:
    optuna = None  # type: ignore[assignment]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20)
    args = parser.parse_args()
    if optuna is None:
        raise SystemExit("optuna not installed")
    print(f"Placeholder: would run {args.trials} Optuna trials on training pipeline.")


if __name__ == "__main__":
    main()
