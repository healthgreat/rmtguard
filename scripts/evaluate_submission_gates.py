from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_STATUS = {"pass", "fail", "pending", "borderline"}
NM_REQUIRED = {
    "synthetic_null_false_signal",
    "diagnostic_no_call_validation",
    "rare_state_retention",
    "real_dataset_count",
    "stability_advantage",
    "annotation_noninferiority",
    "pdac_tme_interpretability",
    "software_release",
    "figure_source_data",
}
GB_REQUIRED = {
    "software_release",
    "real_dataset_count",
    "annotation_noninferiority",
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def gate_status(evidence_rows: list[dict[str, str]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for row in evidence_rows:
        gate_id = row.get("gate_id", "").strip()
        status = row.get("status", "").strip().lower()
        if not gate_id:
            continue
        if status not in VALID_STATUS:
            status = "pending"
        statuses[gate_id] = status
    return statuses


def recommendation(statuses: dict[str, str]) -> str:
    nm_status = [statuses.get(gate, "pending") for gate in NM_REQUIRED]
    gb_status = [statuses.get(gate, "pending") for gate in GB_REQUIRED]

    if all(status == "pass" for status in nm_status):
        return "submit_nature_methods"
    if statuses.get("software_release") == "fail" or statuses.get("annotation_noninferiority") == "fail":
        return "do_not_submit_rework_core_method"
    if all(status in {"pass", "borderline"} for status in gb_status):
        return "prepare_genome_biology_fallback"
    return "continue_benchmarking"


def summarize(gates: list[dict[str, str]], statuses: dict[str, str]) -> list[str]:
    lines = []
    lines.append("RMTGuard submission gate summary")
    lines.append(f"recommendation\t{recommendation(statuses)}")
    lines.append("gate_id\tstatus\tcategory\tnature_methods_requirement")
    for row in gates:
        gate_id = row["gate_id"]
        lines.append(
            "\t".join(
                [
                    gate_id,
                    statuses.get(gate_id, "pending"),
                    row.get("category", ""),
                    row.get("nature_methods_requirement", ""),
                ]
            )
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Nature Methods / Genome Biology submission gates.")
    parser.add_argument("--gates", type=Path, default=ROOT / "metadata" / "submission_gates.tsv")
    parser.add_argument("--evidence", type=Path, default=ROOT / "metadata" / "gate_evidence_template.tsv")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    gates = read_tsv(args.gates)
    evidence = read_tsv(args.evidence)
    statuses = gate_status(evidence)
    lines = summarize(gates, statuses)
    text = "\n".join(lines) + "\n"

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
