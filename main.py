from __future__ import annotations

import argparse
import sys
from pathlib import Path

from translator import translate_sas_to_pyspark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate SAS to PySpark (initial phase)."
    )
    parser.add_argument("sas_file", nargs="?", type=Path, help="Path to SAS file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write PySpark output to file",
    )
    args = parser.parse_args()

    if not args.sas_file:
        parser.print_help()
        return 1

    source = args.sas_file.read_text(encoding="utf-8")
    result = translate_sas_to_pyspark(source)

    if args.output:
        args.output.write_text(result.pyspark, encoding="utf-8")
    else:
        print(result.pyspark)

    if result.diagnostics:
        for diagnostic in result.diagnostics:
            print(diagnostic.format(), file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
