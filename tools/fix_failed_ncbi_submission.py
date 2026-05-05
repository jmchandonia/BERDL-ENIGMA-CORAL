#!/usr/bin/env python3
"""Build cleaned contig FASTA files for NCBI resubmission.

Given a base directory containing report files (for example, report_part1/) and
an original contigs upload directory, this script creates a resubmit directory
with the same FASTA filenames as the original upload directory.

For each RemainingContamination_*.txt report:
- parse contamination spans per contig
- remove those spans from the corresponding contig sequences
- split contaminated contigs into new contigs (A, B, ...)
- drop resulting fragments shorter than --min-length (default 200)

For each Discrepancy_*.txt report:
- parse supported fatal discrepancy issues
- currently trim leading/trailing terminal Ns from flagged contigs

Coverage in renamed contigs is carried over from the parent contig header when
it follows the common SPAdes style:
  <prefix>_length_<N>_cov_<X>
"""

from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterator, List, Optional, Sequence, Tuple


FASTA_SUFFIXES = (".fasta", ".fa", ".fna")
REMAINING_PREFIX = "RemainingContamination_"
DISCREPANCY_PREFIX = "Discrepancy_"
REPORT_SUFFIX = ".txt"
SPADES_NAME_RE = re.compile(
    r"^(?P<prefix>.+?)_length_(?P<length>\d+)_cov_(?P<cov>[0-9]+(?:\.[0-9]+)?)$"
)
SPAN_RE = re.compile(r"(\d+)\.\.(\d+)")
DISCREPANCY_CONTIG_RE = re.compile(
    r"\.sqn:(?P<contig>\S+)\s+\(length\s+(?P<length>\d+),\s+(?P<other>\d+)\s+other\)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create cleaned FASTA files for NCBI resubmission from "
            "RemainingContamination and supported Discrepancy reports."
        )
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help=(
            "Report directory containing RemainingContamination_*.txt and/or "
            "Discrepancy_*.txt files; resubmit/ is created here."
        ),
    )
    parser.add_argument(
        "--contigs-dir",
        required=True,
        help="Original contigs upload directory (for filename mapping).",
    )
    parser.add_argument(
        "--resubmit-subdir",
        default="resubmit",
        help="Output subdirectory under --base-dir (default: resubmit).",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=200,
        help="Minimum output contig length (default: 200).",
    )
    return parser.parse_args()


def iter_fasta_records(path: Path) -> Iterator[Tuple[str, str]]:
    header: Optional[str] = None
    seq_lines: List[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_lines)
                header = line[1:].strip()
                seq_lines = []
                continue
            seq_lines.append(line.strip())
    if header is not None:
        yield header, "".join(seq_lines)


def write_fasta_record(handle, header: str, sequence: str, wrap: int = 80) -> None:
    handle.write(f">{header}\n")
    for start in range(0, len(sequence), wrap):
        handle.write(sequence[start : start + wrap] + "\n")


def report_target_filename(report_path: Path) -> Optional[str]:
    name = report_path.name
    if name.startswith(REMAINING_PREFIX) and name.endswith(REPORT_SUFFIX):
        core = name[len(REMAINING_PREFIX) : -len(REPORT_SUFFIX)]
    elif name.startswith(DISCREPANCY_PREFIX) and name.endswith(REPORT_SUFFIX):
        core = name[len(DISCREPANCY_PREFIX) : -len(REPORT_SUFFIX)]
    else:
        return None
    return core + ".fasta"


def parse_spans_field(span_field: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for match in SPAN_RE.finditer(span_field):
        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            start, end = end, start
        spans.append((start, end))
    return spans


def parse_remaining_report(path: Path) -> Dict[str, List[Tuple[int, int]]]:
    spans_by_contig: DefaultDict[str, List[Tuple[int, int]]] = defaultdict(list)
    in_table = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("Sequence name, length, span(s), apparent source"):
                in_table = True
                continue
            if not in_table:
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                parts = re.split(r"\s{2,}", stripped)
            if len(parts) < 3:
                continue

            contig_name = parts[0].strip()
            spans = parse_spans_field(parts[2])
            if not contig_name or not spans:
                continue
            spans_by_contig[contig_name].extend(spans)

    return dict(spans_by_contig)


def parse_discrepancy_report(path: Path) -> Dict[str, str]:
    fixes_by_contig: Dict[str, str] = {}
    current_issue: Optional[str] = None

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("FATAL:"):
                current_issue = stripped
                continue

            match = DISCREPANCY_CONTIG_RE.search(stripped)
            if not match or current_issue is None:
                continue

            if "TERMINAL_NS" in current_issue:
                fixes_by_contig[match.group("contig")] = "trim_terminal_ns"

    return fixes_by_contig


def merge_spans(spans: Sequence[Tuple[int, int]], max_len: int) -> List[Tuple[int, int]]:
    clipped: List[Tuple[int, int]] = []
    for start, end in spans:
        start = max(1, min(start, max_len))
        end = max(1, min(end, max_len))
        if start > end:
            continue
        clipped.append((start, end))
    if not clipped:
        return []

    clipped.sort(key=lambda x: (x[0], x[1]))
    merged: List[Tuple[int, int]] = [clipped[0]]
    for start, end in clipped[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def keep_segments_after_removal(
    sequence: str,
    spans: Sequence[Tuple[int, int]],
) -> List[Tuple[int, int, str]]:
    seq_len = len(sequence)
    merged = merge_spans(spans, seq_len)
    if not merged:
        return [(1, seq_len, sequence)] if seq_len > 0 else []

    segments: List[Tuple[int, int, str]] = []
    cursor = 1
    for start, end in merged:
        if cursor < start:
            seg_start = cursor
            seg_end = start - 1
            segments.append((seg_start, seg_end, sequence[seg_start - 1 : seg_end]))
        cursor = end + 1
    if cursor <= seq_len:
        segments.append((cursor, seq_len, sequence[cursor - 1 : seq_len]))
    return segments


def index_to_letters(index: int) -> str:
    # 1 -> A, 26 -> Z, 27 -> AA
    letters: List[str] = []
    value = index
    while value > 0:
        value -= 1
        letters.append(chr(ord("A") + (value % 26)))
        value //= 26
    return "".join(reversed(letters))


def make_split_contig_name(parent_id: str, fragment_index: int, new_len: int) -> str:
    suffix = index_to_letters(fragment_index)
    match = SPADES_NAME_RE.match(parent_id)
    if match:
        prefix = match.group("prefix")
        cov = match.group("cov")
        return f"{prefix}{suffix}_length_{new_len}_cov_{cov}"
    return f"{parent_id}{suffix}_length_{new_len}"


def update_contig_header_length(header: str, new_len: int) -> str:
    parts = header.split(maxsplit=1)
    contig_id = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    match = SPADES_NAME_RE.match(contig_id)
    if match:
        contig_id = (
            f"{match.group('prefix')}_length_{new_len}_cov_{match.group('cov')}"
        )

    return f"{contig_id} {remainder}".rstrip()


def trim_terminal_ns(sequence: str) -> Tuple[str, int, int]:
    start_trim = len(sequence) - len(sequence.lstrip("Nn"))
    end_trim = len(sequence) - len(sequence.rstrip("Nn"))
    trimmed = sequence[start_trim : len(sequence) - end_trim if end_trim else len(sequence)]
    return trimmed, start_trim, end_trim


def process_fasta(
    input_fasta: Path,
    output_fasta: Path,
    spans_by_contig: Dict[str, List[Tuple[int, int]]],
    discrepancy_fixes: Dict[str, str],
    min_length: int,
) -> Dict[str, int]:
    stats = {
        "input_contigs": 0,
        "output_contigs": 0,
        "contigs_with_spans": 0,
        "contigs_with_discrepancies": 0,
        "fragments_removed_short": 0,
        "spans_total": sum(len(v) for v in spans_by_contig.values()),
        "terminal_ns_trimmed": 0,
    }

    output_fasta.parent.mkdir(parents=True, exist_ok=True)
    with output_fasta.open("w", encoding="utf-8") as out_handle:
        for header, sequence in iter_fasta_records(input_fasta):
            stats["input_contigs"] += 1
            contig_id = header.split()[0]
            spans = spans_by_contig.get(contig_id, [])
            discrepancy_fix = discrepancy_fixes.get(contig_id)
            if not spans and not discrepancy_fix:
                write_fasta_record(out_handle, header, sequence)
                stats["output_contigs"] += 1
                continue

            if spans:
                stats["contigs_with_spans"] += 1
            if discrepancy_fix:
                stats["contigs_with_discrepancies"] += 1

            segments = keep_segments_after_removal(sequence, spans)
            fragment_index = 0
            for _, _, seg_seq in segments:
                if discrepancy_fix == "trim_terminal_ns":
                    seg_seq, start_trim, end_trim = trim_terminal_ns(seg_seq)
                    stats["terminal_ns_trimmed"] += start_trim + end_trim

                seg_len = len(seg_seq)
                if seg_len < min_length:
                    stats["fragments_removed_short"] += 1
                    continue

                if spans:
                    fragment_index += 1
                    output_header = make_split_contig_name(contig_id, fragment_index, seg_len)
                else:
                    output_header = update_contig_header_length(header, seg_len)

                write_fasta_record(out_handle, output_header, seg_seq)
                stats["output_contigs"] += 1

    return stats


def main() -> None:
    args = parse_args()

    base_dir = Path(args.base_dir)
    contigs_dir = Path(args.contigs_dir)
    report_dir = base_dir
    resubmit_dir = base_dir / args.resubmit_subdir

    if not base_dir.is_dir():
        raise SystemExit(f"ERROR: report directory does not exist: {report_dir}")
    if not contigs_dir.is_dir():
        raise SystemExit(f"ERROR: contigs directory does not exist: {contigs_dir}")

    remaining_reports = sorted(report_dir.glob(f"{REMAINING_PREFIX}*{REPORT_SUFFIX}"))
    discrepancy_reports = sorted(report_dir.glob(f"{DISCREPANCY_PREFIX}*{REPORT_SUFFIX}"))
    report_files = remaining_reports + discrepancy_reports
    if not report_files:
        raise SystemExit(
            f"ERROR: no {REMAINING_PREFIX}*{REPORT_SUFFIX} or "
            f"{DISCREPANCY_PREFIX}*{REPORT_SUFFIX} files found in {report_dir}"
        )

    contig_files = sorted(
        p for p in contigs_dir.iterdir() if p.is_file() and p.suffix.lower() in FASTA_SUFFIXES
    )
    if not contig_files:
        raise SystemExit(f"ERROR: no FASTA files found in contigs directory: {contigs_dir}")

    remaining_by_filename: Dict[str, Path] = {}
    discrepancy_by_filename: Dict[str, Path] = {}
    for report_path in report_files:
        target_name = report_target_filename(report_path)
        if not target_name:
            continue
        if report_path.name.startswith(REMAINING_PREFIX):
            remaining_by_filename[target_name] = report_path
        elif report_path.name.startswith(DISCREPANCY_PREFIX):
            discrepancy_by_filename[target_name] = report_path

    if resubmit_dir.exists():
        shutil.rmtree(resubmit_dir)
    resubmit_dir.mkdir(parents=True, exist_ok=True)

    print(f"Base directory: {base_dir}")
    print(f"Report directory: {report_dir}")
    print(f"Contigs directory: {contigs_dir}")
    print(f"Resubmit directory: {resubmit_dir}")

    total_input_contigs = 0
    total_output_contigs = 0
    total_spans = 0
    total_contigs_with_spans = 0
    total_contigs_with_discrepancies = 0
    total_removed_short = 0
    total_terminal_ns_trimmed = 0
    reports_used = 0

    contigs_by_name = {p.name: p for p in contig_files}

    for fasta_name, report_path in sorted(
        {**remaining_by_filename, **discrepancy_by_filename}.items()
    ):
        if fasta_name not in contigs_by_name:
            print(
                f"WARNING: report {report_path.name} maps to {fasta_name}, "
                "but that file is not present in --contigs-dir"
            )

    for input_fasta in contig_files:
        remaining_report = remaining_by_filename.get(input_fasta.name)
        discrepancy_report = discrepancy_by_filename.get(input_fasta.name)
        if remaining_report is None and discrepancy_report is None:
            continue
        output_fasta = resubmit_dir / input_fasta.name

        spans_by_contig = (
            parse_remaining_report(remaining_report) if remaining_report else {}
        )
        discrepancy_fixes = (
            parse_discrepancy_report(discrepancy_report) if discrepancy_report else {}
        )
        stats = process_fasta(
            input_fasta=input_fasta,
            output_fasta=output_fasta,
            spans_by_contig=spans_by_contig,
            discrepancy_fixes=discrepancy_fixes,
            min_length=args.min_length,
        )
        reports_used += int(remaining_report is not None) + int(discrepancy_report is not None)
        total_input_contigs += stats["input_contigs"]
        total_output_contigs += stats["output_contigs"]
        total_spans += stats["spans_total"]
        total_contigs_with_spans += stats["contigs_with_spans"]
        total_contigs_with_discrepancies += stats["contigs_with_discrepancies"]
        total_removed_short += stats["fragments_removed_short"]
        total_terminal_ns_trimmed += stats["terminal_ns_trimmed"]
        print(
            f"Processed {input_fasta.name}: "
            f"contigs_with_spans={stats['contigs_with_spans']} "
            f"contigs_with_discrepancies={stats['contigs_with_discrepancies']} "
            f"spans={stats['spans_total']} "
            f"terminal_ns_trimmed={stats['terminal_ns_trimmed']} "
            f"output_contigs={stats['output_contigs']}"
        )

    print("Done")
    print(f"Reports used: {reports_used}")
    print(f"Total spans applied: {total_spans}")
    print(f"Contigs with contamination spans: {total_contigs_with_spans}")
    print(f"Contigs with supported discrepancy fixes: {total_contigs_with_discrepancies}")
    print(f"Total terminal Ns trimmed: {total_terminal_ns_trimmed}")
    print(f"Fragments removed (<{args.min_length} nt): {total_removed_short}")
    print(f"Total input contaminated contigs counted: {total_input_contigs}")
    print(f"Total output contaminated contigs written: {total_output_contigs}")


if __name__ == "__main__":
    main()
