#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    smart_common_dir = Path(__file__).resolve().parents[1]
    migrator_dir = smart_common_dir.parent / "smart-db-migrator"

    print(
        "Migration apply was moved out of smart-common.\n"
        f"Use smart-db-migrator instead: cd {migrator_dir} && make apply-dev",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
