"""Command-line interface: ``imdtrack update`` / ``info`` / ``export`` / ``build``."""
from __future__ import annotations

import argparse
import sys

from .core import load


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="imdtrack", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_up = sub.add_parser("update", help="Refresh the published dataset from GitHub (if changed).")
    p_up.add_argument("--source", choices=["github", "imd"], default="github",
                      help="github (default): pull the pre-parsed dataset; imd: parse the workbook.")
    p_up.add_argument("--force", action="store_true", help="Re-download even if unchanged.")

    p_info = sub.add_parser("info", help="Show a summary of the cached record.")
    p_info.add_argument("--source", choices=["github", "imd"], default="github")

    p_ex = sub.add_parser("export", help="Export the observations table to CSV/Parquet.")
    p_ex.add_argument("out", help="Output path (.csv or .parquet).")
    p_ex.add_argument("--source", choices=["github", "imd"], default="github")
    p_ex.add_argument("--update", action="store_true", help="Refresh from source first.")

    p_build = sub.add_parser(
        "build",
        help="Pipeline: fetch the IMD workbook, parse, validate, and write data/ (CI).",
    )
    p_build.add_argument("--data-dir", default=None, help="Output directory (default: ./data).")
    p_build.add_argument("--force", action="store_true", help="Rebuild even if unchanged.")

    args = p.parse_args(argv)

    if args.cmd == "build":
        from pathlib import Path

        from . import _repo
        from .pipeline import main as build_main

        data_dir = args.data_dir or _repo.DATA_DIR_NAME
        return build_main(["--data-dir", str(Path(data_dir))] + (["--force"] if args.force else []))

    if args.cmd == "update":
        bt = load(update=True, source=args.source, force=args.force)
        print(f"Updated: {bt!r}")
    elif args.cmd == "info":
        bt = load(source=args.source)
        print(repr(bt))
        if not bt.storms.empty:
            print(bt.storms[["storm_id", "name", "basin", "start_time", "peak_grade",
                             "max_wind", "min_pressure"]].tail(10).to_string(index=False))
    elif args.cmd == "export":
        bt = load(source=args.source, update=args.update)
        if args.out.endswith(".parquet"):
            bt.observations.to_parquet(args.out, index=False)
        else:
            bt.observations.to_csv(args.out, index=False)
        print(f"Wrote {len(bt.observations)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
