from __future__ import annotations

import runpy
import shutil
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parent


def run_step(relative_path: str) -> None:
    script = CASE_DIR / relative_path
    print(f"\n==> {relative_path}")
    runpy.run_path(str(script), run_name="__main__")


def main() -> None:
    run_step("etl/01_build_stage.py")
    run_step("etl/02_build_clean.py")
    run_step("etl/03_build_reports.py")
    run_step("app/build_visibility.py")
    site_dir = CASE_DIR / "site"
    if site_dir.exists():
        reports_target = site_dir / "dist" / "data" / "reports"
        reports_target.mkdir(parents=True, exist_ok=True)
        for csv_file in (CASE_DIR / "data" / "reports").glob("*.csv"):
            shutil.copyfile(csv_file, reports_target / csv_file.name)
        shutil.copyfile(CASE_DIR / "app_runtime" / "index.html", site_dir / "dist" / "index.html")
    print("\nListo. Abrir http://localhost:8000/app_runtime/index.html con servidor local.")


if __name__ == "__main__":
    main()
