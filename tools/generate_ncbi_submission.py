"""
Generate NCBI SRA and Genome submission templates from BERDL provenance data.

This script walks provenance from genomes to find:
1. Raw reads with FASTQ files on genomics.lbl.gov
2. Samples used to isolate strains
3. Protocols used for sequencing and assembly
4. Location information for biosamples

It generates:
- Biosample table (SRA Microbe 1.0 package)
- SRA metadata table for FASTQ submissions
- Genome metadata table for FASTA contig submissions
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pathlib import Path
import sys
from openpyxl import load_workbook
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.walk_provenance import (  # noqa: E402
    discover_tables,
    get_table_schema,
    load_process_cache,
    NameResolver,
    parse_token,
    select_all_rows,
    set_debug,
    walk_provenance,
)
from tools import walk_provenance as walk_provenance_module  # noqa: E402


FASTQ_HOST = "genomics.lbl.gov"
DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"
DEFAULT_OUTPUT_DIR = "ncbi_submission"
DEFAULT_EDR_PATH = "/mnt/net/dipa.jmcnet/data/edr"
EDR_URL_PREFIX = "https://genomics.lbl.gov/enigma-data/"
PROTOCOL_TABLE = "sdt_protocol"
READ_COVERAGE_TABLE = "ddt_brick0000521"
READ_COVERAGE_COLUMN = "read_coverage_statistic_average_count_unit"
Bacteria_AVAILABLE_FROM = (
    "Romy Chakraborty Lab, Berkeley National Lab, Berkeley CA, USA"
)
BIOSAMPLE_TEMPLATE_CANDIDATES = [
    REPO_ROOT / "templates" / "Microbe.1.0.xlsx",
    Path("ncbi_submission") / "Microbe.1.0.xlsx",
    Path("ncbi_submission") / "MIcrobe.1.0.xlsx",
    Path("genome_upload") / "ncbi_submission" / "Microbe.1.0.xlsx",
]
SRA_TEMPLATE_CANDIDATES = [
    REPO_ROOT / "templates" / "SRA_metadata.xlsx",
    Path("ncbi_submission") / "SRA_metadata.xlsx",
    Path("genome_upload") / "ncbi_submission" / "SRA_metadata.xlsx",
]
GENOME_TEMPLATE_CANDIDATES = [
    REPO_ROOT / "templates" / "Template_GenomeBatch.xlsx",
    Path("ncbi_submission") / "Template_GenomeBatch.xlsx",
    Path("genome_upload") / "ncbi_submission" / "Template_GenomeBatch.xlsx",
]


def log_info(message: str) -> None:
    print(f"[info] {message}", file=sys.stderr)


def log_debug(message: str, enabled: bool) -> None:
    if enabled:
        print(f"[debug] {message}", file=sys.stderr)


def _format_json_for_log(value: Any, fallback: str = "<unavailable>") -> str:
    if value is None:
        return fallback
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


def log_request_failure(
    exc: requests.HTTPError,
    payload: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
) -> None:
    request = getattr(exc, "request", None)
    response = exc.response
    request_url = getattr(request, "url", None) or getattr(response, "url", None)
    if not request_url and path:
        request_url = f"{walk_provenance_module.BASE_URL}{path}"

    log_info(f"HTTP request failed: {exc}")
    log_info(f"Failed URL: {request_url or '<unknown>'}")
    if payload is not None:
        log_info(f"Failed payload: {_format_json_for_log(payload)}")
    if response is not None:
        body = (response.text or "").strip()
        if body:
            if len(body) > 2000:
                body = f"{body[:2000]}... [truncated]"
            log_info(f"Response body: {body}")


def enable_request_failure_logging() -> None:
    if getattr(walk_provenance_module, "_generate_ncbi_post_json_wrapped", False):
        return

    original_post_json = walk_provenance_module.post_json

    def wrapped_post_json(path: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Any:
        try:
            return original_post_json(path, payload, headers)
        except requests.HTTPError as exc:
            log_request_failure(exc, payload=payload, path=path)
            raise

    walk_provenance_module.post_json = wrapped_post_json
    walk_provenance_module._generate_ncbi_post_json_wrapped = True


def get_headers() -> Dict[str, str]:
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        raise RuntimeError("KB_AUTH_TOKEN must be set in the environment.")
    return {"Authorization": f"Bearer {token}"}


def get_table_columns(
    headers: Dict[str, str], table: str, cache: Dict[str, List[str]]
) -> List[str]:
    if table in cache:
        return cache[table]
    columns = get_table_schema(headers, table)
    cache[table] = columns
    return columns


def select_first_row(
    headers: Dict[str, str],
    table: str,
    filters: List[Dict[str, Any]],
    columns: Sequence[str],
) -> Optional[Dict[str, Any]]:
    rows = select_all_rows(headers, table, columns=columns, filters=filters, limit=1)
    return rows[0] if rows else None


def select_row_by_id(
    headers: Dict[str, str],
    table: str,
    obj_id: str,
    columns: Sequence[str],
) -> Optional[Dict[str, Any]]:
    id_col = f"{table}_id"
    filters = [{"column": id_col, "operator": "=", "value": obj_id}]
    return select_first_row(headers, table, filters, columns)


def normalize_protocol_names(protocol_field: Any) -> List[str]:
    if protocol_field is None:
        return []
    if isinstance(protocol_field, list):
        return [str(p).strip() for p in protocol_field if str(p).strip()]
    if isinstance(protocol_field, str):
        parts = [p.strip() for p in protocol_field.split(",")]
        return [p for p in parts if p]
    return [str(protocol_field).strip()]


def parse_protocol_metadata(protocol_name: str, description: str) -> Dict[str, Optional[str]]:
    name_lower = (protocol_name or "").lower()
    desc_lower = (description or "").lower()

    sequencing_tech = None
    machine_type = None
    program_version = None

    if "novaseq" in name_lower or "novaseq" in desc_lower:
        if "xplus" in name_lower or "x plus" in desc_lower:
            machine_type = "NovaSeq X Plus"
        elif "6000" in name_lower or "6000" in desc_lower:
            machine_type = "NovaSeq 6000"
        else:
            machine_type = "NovaSeq"
        sequencing_tech = "Illumina"
    elif "hiseq" in name_lower or "hiseq" in desc_lower:
        machine_type = "HiSeq 4000"
        sequencing_tech = "Illumina"
    elif "nextseq" in name_lower or "nextseq" in desc_lower:
        if "2000" in name_lower or "2000" in desc_lower:
            machine_type = "NextSeq 2000"
        elif "500" in name_lower or "500" in desc_lower:
            machine_type = "NextSeq 500"
        else:
            machine_type = "NextSeq"
        sequencing_tech = "Illumina"
    elif "promethion" in name_lower or "promethion" in desc_lower:
        machine_type = "PromethION"
        sequencing_tech = "Oxford Nanopore"
    elif "pacbio" in name_lower or "pacbio" in desc_lower:
        sequencing_tech = "PacBio"
        if "hifi" in name_lower or "hifi" in desc_lower:
            machine_type = "PacBio HiFi"
    elif "minion" in name_lower or "minion" in desc_lower:
        machine_type = "MinION"
        sequencing_tech = "Oxford Nanopore"

    version_patterns = [
        (r"spades\s+v?(\d+\.\d+\.\d+)", "spades"),
        (r"cutadapt\s+v?(\d+\.\d+)", "cutadapt"),
        (r"trimmomatic\s+v?(\d+\.\d+)", "trimmomatic"),
        (r"prokka\s+v?(\d+\.\d+)", "prokka"),
        (r"prodigal", "prodigal"),
        (r"flye\s+v?(\d+\.\d+)", "flye"),
        (r"canu\s+v?(\d+\.\d+)", "canu"),
        (r"metaspades", "metaspades"),
        (r"unicycler", "unicycler"),
    ]

    for pattern, program in version_patterns:
        match = re.search(pattern, description or "", re.IGNORECASE)
        if match:
            if program == "prodigal":
                program_version = "Prodigal"
            elif program == "metaspades":
                program_version = "MetaSPAdes"
            elif program == "unicycler":
                program_version = "Unicycler"
            else:
                version = match.group(1) if match.groups() else ""
                program_version = f"{program.capitalize()} {version}".strip()
            break

    return {
        "sequencing_technology": sequencing_tech,
        "machine_type": machine_type,
        "program_version": program_version,
    }


def is_paired_read_type(read_type: Optional[str]) -> bool:
    if not read_type:
        return False
    read_type_lower = read_type.lower()
    return "paired" in read_type_lower or "pair" in read_type_lower


def get_protocol_info(
    headers: Dict[str, str],
    protocol_name: str,
    column_cache: Dict[str, List[str]],
    info_cache: Dict[str, Dict[str, Optional[str]]],
) -> Dict[str, Optional[str]]:
    if protocol_name in info_cache:
        return info_cache[protocol_name]

    columns = get_table_columns(headers, PROTOCOL_TABLE, column_cache)
    desired = [col for col in ["sdt_protocol_name", "sdt_protocol_description", "link"] if col in columns]
    if not desired:
        info_cache[protocol_name] = {}
        return info_cache[protocol_name]

    row = select_first_row(
        headers,
        PROTOCOL_TABLE,
        [{"column": "sdt_protocol_name", "operator": "=", "value": protocol_name}],
        desired,
    )
    if row is None and "sdt_protocol_id" in columns:
        row = select_first_row(
            headers,
            PROTOCOL_TABLE,
            [{"column": "sdt_protocol_id", "operator": "=", "value": protocol_name}],
            desired,
        )

    name = row.get("sdt_protocol_name") if row else protocol_name
    description = row.get("sdt_protocol_description") if row else ""
    metadata = parse_protocol_metadata(name or protocol_name, description or "")
    metadata["protocol_name"] = name or protocol_name
    metadata["protocol_description"] = description or ""
    metadata["protocol_link"] = row.get("link") if row else None
    info_cache[protocol_name] = metadata
    return metadata


def find_oldest_reads_with_fastq(
    genome_token: str,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    downstream_lookup: Dict[str, List[Dict[str, Any]]],
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    read_cache: Dict[str, Dict[str, Any]],
    strain_token: Optional[str] = None,
    log_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    def read_link_ok(link: Optional[str]) -> bool:
        if not link:
            return False
        link_lower = link.lower()
        if FASTQ_HOST not in link_lower:
            return False
        return ".fastq" in link_lower or ".fq" in link_lower

    def get_reads_data(obj_id: str) -> Dict[str, Any]:
        if obj_id in read_cache:
            return read_cache[obj_id]
        columns = get_table_columns(headers, "sdt_reads", column_cache)
        desired = [
            col
            for col in [
                "sdt_reads_id",
                "sdt_reads_name",
                "link",
                "read_type_sys_oterm_name",
                "sequencing_technology_sys_oterm_name",
            ]
            if col in columns
        ]
        row = select_row_by_id(headers, "sdt_reads", obj_id, desired)
        reads_data = row or {}
        read_cache[obj_id] = reads_data
        return reads_data

    def reads_process_flags(reads_token: str) -> Tuple[bool, bool]:
        produced_by_copy = False
        processed = False
        for proc in out_lookup.get(reads_token, []):
            process_name = (proc.get("process_term_name") or "").lower()
            if "copy data" in process_name:
                produced_by_copy = True
            if "cutadapt" in process_name or "trimmomatic" in process_name:
                processed = True
        return produced_by_copy, processed

    def collect_reads_protocols(reads_token: str) -> List[str]:
        shotgun_protocols: List[str] = []
        other_protocols: List[str] = []

        def add_protocols(proc: Dict[str, Any]) -> None:
            process_name = (proc.get("process_term_name") or "").lower()
            normalized = normalize_protocol_names(proc.get("protocol"))
            if not normalized:
                return
            if (
                "shotgun sequencing and assembly" in process_name
                or "shotgun sequencing" in process_name
                or "sequencing" in process_name
            ):
                shotgun_protocols.extend(normalized)
            else:
                other_protocols.extend(normalized)

        for proc in out_lookup.get(reads_token, []):
            add_protocols(proc)
        for proc in downstream_lookup.get(reads_token, []):
            add_protocols(proc)

        ordered = shotgun_protocols + other_protocols
        seen: set[str] = set()
        unique = []
        for name in ordered:
            if name in seen:
                continue
            seen.add(name)
            unique.append(name)
        return unique

    def collect_reads_inputs(start_token: str) -> List[str]:
        visited: set[str] = set()
        reads_inputs: List[str] = []

        def walk_upstream(obj_token: str) -> None:
            if obj_token in visited:
                return
            visited.add(obj_token)

            table_name, obj_id = parse_token(obj_token)
            if not table_name or not obj_id:
                return

            if table_name == "sdt_reads":
                reads_inputs.append(obj_token)
                return

            proc_list = out_lookup.get(obj_token, [])
            for proc in proc_list:
                process_name = (proc.get("process_term_name") or "").lower()
                if table_name in ["sdt_assembly", "sdt_genome"]:
                    for inp in proc.get("input_objs", []):
                        walk_upstream(inp)
                else:
                    for inp in proc.get("input_objs", []):
                        inp_table, _ = parse_token(inp)
                        if inp_table in ["sdt_reads", "sdt_assembly"]:
                            walk_upstream(inp)

        walk_upstream(start_token)
        seen: set[str] = set()
        unique_reads = []
        for token in reads_inputs:
            if token in seen:
                continue
            seen.add(token)
            unique_reads.append(token)
        return unique_reads

    def collect_ancestral_reads(start_reads_token: str) -> List[str]:
        visited: set[str] = set()
        ancestors: List[str] = []

        def walk_upstream(reads_token: str) -> None:
            if reads_token in visited:
                return
            visited.add(reads_token)

            table_name, _ = parse_token(reads_token)
            if table_name != "sdt_reads":
                return

            upstream_reads: List[str] = []
            for proc in out_lookup.get(reads_token, []):
                process_name = (proc.get("process_term_name") or "").lower()
                if "reads processing" in process_name or "copy data" in process_name:
                    for inp in proc.get("input_objs", []):
                        inp_table, _ = parse_token(inp)
                        if inp_table == "sdt_reads":
                            upstream_reads.append(inp)

            if not upstream_reads:
                ancestors.append(reads_token)
                return

            for inp in upstream_reads:
                walk_upstream(inp)

        walk_upstream(start_reads_token)
        seen: set[str] = set()
        unique_reads = []
        for token in ancestors:
            if token in seen:
                continue
            seen.add(token)
            unique_reads.append(token)
        return unique_reads

    def collect_reads_downstream(
        start_token: str, only_copy: bool
    ) -> List[Dict[str, Any]]:
        visited: set[str] = set()
        reads_candidates: List[Dict[str, Any]] = []

        def walk_downstream(
            obj_token: str,
            depth: int = 0,
            path: Optional[List[str]] = None,
            parent_token: Optional[str] = None,
            parent_process: Optional[str] = None,
        ) -> None:
            if path is None:
                path = []
            if obj_token in visited:
                return
            visited.add(obj_token)

            table_name, obj_id = parse_token(obj_token)
            if not table_name or not obj_id:
                return

            current_path = path + [obj_token]

            if table_name == "sdt_reads":
                reads_data = get_reads_data(obj_id)
                link = reads_data.get("link")
                if read_link_ok(link):
                    protocols = collect_reads_protocols(obj_token)
                    produced_by_copy, processed = reads_process_flags(obj_token)
                    reads_candidates.append(
                        {
                            "reads_id": obj_id,
                            "reads_name": reads_data.get("sdt_reads_name"),
                            "link": link,
                            "read_type": reads_data.get("read_type_sys_oterm_name"),
                            "sequencing_technology": reads_data.get(
                                "sequencing_technology_sys_oterm_name"
                            ),
                            "protocols": sorted(set(protocols)),
                            "depth": depth,
                            "path": current_path.copy(),
                            "produced_by_copy_data": produced_by_copy,
                            "processed_by_trim": processed,
                            "reads_token": obj_token,
                            "parent_reads_token": parent_token,
                            "parent_process_name": parent_process,
                        }
                    )

            for proc in downstream_lookup.get(obj_token, []):
                process_name = (proc.get("process_term_name") or "").lower()
                if only_copy and "copy data" not in process_name:
                    continue
                out_token = proc.get("output_obj")
                if out_token:
                    walk_downstream(
                        out_token,
                        depth + 1,
                        current_path,
                        parent_token=obj_token,
                        parent_process=proc.get("process_term_name"),
                    )

        walk_downstream(start_token)
        return reads_candidates

    def log_reads(message: str, reads_list: List[Dict[str, Any]]) -> None:
        prefix = log_label or ""
        if not reads_list:
            log_info(f"{prefix}{message}: none")
            return
        details = ", ".join(
            f"{r.get('reads_id')}:{r.get('reads_name')}" for r in reads_list
        )
        log_info(f"{prefix}{message}: {details}")

    def log_reads_detail(message: str, reads_list: List[Dict[str, Any]]) -> None:
        prefix = log_label or ""
        log_info(f"{prefix}{message}: {len(reads_list)}")
        for reads in reads_list:
            log_info(
                f"{prefix}  - id={reads.get('reads_id')} "
                f"name={reads.get('reads_name')!r} "
                f"read_type={reads.get('read_type')!r} "
                f"produced_by_copy={reads.get('produced_by_copy_data')} "
                f"processed_by_trim={reads.get('processed_by_trim')} "
                f"parent_reads={reads.get('parent_reads_token')!r} "
                f"parent_process={reads.get('parent_process_name')!r} "
                f"link={reads.get('link')!r}"
            )

    def choose_paired_from_group(reads_group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(reads_group) <= 1:
            return reads_group
        r1 = None
        r2 = None
        for reads in reads_group:
            name_lower = (reads.get("reads_name") or "").lower()
            link_lower = (reads.get("link") or "").lower()
            marker = f"{name_lower} {link_lower}"
            if any(x in marker for x in ["_r1", "_1.fastq", "_1.fq"]):
                r1 = reads
            elif any(x in marker for x in ["_r2", "_2.fastq", "_2.fq"]):
                r2 = reads
        if r1 and r2:
            return [r1, r2]
        return reads_group

    def get_reads_protocols(reads_token: str) -> List[str]:
        return collect_reads_protocols(reads_token)

    def select_best_reads(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        if len(candidates) == 1:
            return candidates
        grouped: Dict[Tuple[Optional[str], str], List[Dict[str, Any]]] = defaultdict(list)
        for reads in candidates:
            parent_token = reads.get("parent_reads_token")
            parent_process = (reads.get("parent_process_name") or "").lower()
            grouped[(parent_token, parent_process)].append(reads)
        copy_groups = {
            key: group
            for key, group in grouped.items()
            if "copy data" in key[1]
        }
        if copy_groups:
            grouped = copy_groups
        best_group = None
        best_pair = []
        for parent_token, group in grouped.items():
            pair = choose_paired_from_group(group)
            if len(pair) >= 2:
                best_group = group
                best_pair = pair
                break
        if best_pair:
            log_reads_detail("Selected paired reads from same parent", best_pair)
            return best_pair
        if len(grouped) == 1:
            only_group = next(iter(grouped.values()))
            return only_group
        best_group = max(grouped.values(), key=len)
        log_reads_detail("Selected reads from largest parent group", best_group)
        return best_group

    def select_submission_reads(
        ancestor_reads_token: str,
        ancestor_protocols: List[str],
        ancestor_seq_tech: Optional[str],
    ) -> List[Dict[str, Any]]:
        table_name, obj_id = parse_token(ancestor_reads_token)
        if table_name == "sdt_reads" and obj_id:
            ancestor_data = get_reads_data(obj_id)
            if read_link_ok(ancestor_data.get("link")):
                chosen = [
                    {
                        "reads_id": obj_id,
                        "reads_name": ancestor_data.get("sdt_reads_name"),
                        "link": ancestor_data.get("link"),
                        "read_type": ancestor_data.get("read_type_sys_oterm_name"),
                        "sequencing_technology": ancestor_data.get(
                            "sequencing_technology_sys_oterm_name"
                        ),
                        "protocols": ancestor_protocols,
                        "depth": 0,
                        "path": [ancestor_reads_token],
                        "produced_by_copy_data": False,
                        "processed_by_trim": False,
                        "reads_token": ancestor_reads_token,
                        "parent_reads_token": None,
                        "parent_process_name": None,
                    }
                ]
                for reads in chosen:
                    reads["source_reads_token"] = ancestor_reads_token
                    reads["source_protocols"] = ancestor_protocols
                    reads["source_sequencing_technology"] = ancestor_seq_tech
                return chosen

        copy_candidates = collect_reads_downstream(ancestor_reads_token, only_copy=True)
        if copy_candidates:
            log_reads_detail("Copy-data FASTQ candidates", copy_candidates)
            chosen = select_best_reads(copy_candidates)
        else:
            all_candidates = collect_reads_downstream(ancestor_reads_token, only_copy=False)
            log_reads_detail("All downstream FASTQ candidates", all_candidates)
            chosen = select_best_reads(all_candidates)

        for reads in chosen:
            reads["source_reads_token"] = ancestor_reads_token
            reads["source_protocols"] = ancestor_protocols
            reads["source_sequencing_technology"] = ancestor_seq_tech
        return chosen

    reads_inputs = collect_reads_inputs(genome_token)
    if reads_inputs:
        log_info(f"{log_label or ''}Assembly reads inputs: {len(reads_inputs)}")
    selected_reads: List[Dict[str, Any]] = []
    for reads_input in reads_inputs:
        ancestral_reads = collect_ancestral_reads(reads_input)
        if not ancestral_reads:
            continue
        for ancestor_token in ancestral_reads:
            table_name, obj_id = parse_token(ancestor_token)
            if table_name != "sdt_reads" or not obj_id:
                continue
            ancestor_data = get_reads_data(obj_id)
            ancestor_protocols = get_reads_protocols(ancestor_token)
            ancestor_seq_tech = ancestor_data.get("sequencing_technology_sys_oterm_name")
            submissions = select_submission_reads(
                ancestor_token, ancestor_protocols, ancestor_seq_tech
            )
            if submissions:
                selected_reads.extend(submissions)

    if selected_reads:
        seen_ids: set[str] = set()
        unique_reads: List[Dict[str, Any]] = []
        for reads in selected_reads:
            reads_id = reads.get("reads_id")
            if reads_id in seen_ids:
                continue
            if reads_id:
                seen_ids.add(reads_id)
            unique_reads.append(reads)
        log_reads("Selected reads", unique_reads)
        return unique_reads

    if strain_token:
        downstream_candidates = collect_reads_downstream(strain_token, only_copy=False)
        if downstream_candidates:
            log_reads("Found strain-downstream reads", downstream_candidates)
        if downstream_candidates:
            return downstream_candidates

    return []


def find_samples_from_genome(
    genome_token: str,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    visited: set[str] = set()
    samples_found: List[Dict[str, Any]] = []

    def walk_upstream(obj_token: str, current_protocol: Optional[str] = None) -> None:
        if obj_token in visited:
            return
        visited.add(obj_token)

        table_name, obj_id = parse_token(obj_token)
        if not table_name or not obj_id:
            return

        if table_name == "sdt_sample":
            columns = get_table_columns(headers, "sdt_sample", column_cache)
            desired = [
                col
                for col in [
                    "sdt_sample_id",
                    "sdt_sample_name",
                    "sdt_location_name",
                    "date",
                    "depth_meter",
                    "material_sys_oterm_name",
                    "sdt_sample_description",
                ]
                if col in columns
            ]
            sample_row = select_row_by_id(headers, "sdt_sample", obj_id, desired)
            if sample_row:
                samples_found.append(
                    {
                        "sample_id": obj_id,
                        "sample_name": sample_row.get("sdt_sample_name"),
                        "sample_token": f"sdt_sample:{obj_id}",
                        "location_name": sample_row.get("sdt_location_name"),
                        "date": sample_row.get("date"),
                        "depth_meter": sample_row.get("depth_meter"),
                        "material_name": sample_row.get("material_sys_oterm_name"),
                        "description": sample_row.get("sdt_sample_description"),
                        "protocol": current_protocol,
                    }
                )

        for proc in out_lookup.get(obj_token, []):
            protocol = proc.get("protocol") or current_protocol
            for inp in proc.get("input_objs", []):
                if table_name == "sdt_sample":
                    walk_upstream(inp, protocol)
                else:
                    walk_upstream(inp, current_protocol)

    walk_upstream(genome_token)

    seen_ids: set[str] = set()
    unique_samples = []
    for sample in samples_found:
        if sample["sample_id"] in seen_ids:
            continue
        seen_ids.add(sample["sample_id"])
        unique_samples.append(sample)
    return unique_samples


def get_location_info(
    headers: Dict[str, str],
    location_name: str,
    column_cache: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    if not location_name:
        return None
    columns = get_table_columns(headers, "sdt_location", column_cache)
    desired = [
        col
        for col in [
            "sdt_location_name",
            "latitude_degree",
            "longitude_degree",
            "country_sys_oterm_name",
            "region",
            "biome_sys_oterm_name",
        ]
        if col in columns
    ]
    row = select_first_row(
        headers,
        "sdt_location",
        [{"column": "sdt_location_name", "operator": "=", "value": location_name}],
        desired,
    )
    if not row:
        return None
    return {
        "location_name": location_name,
        "latitude": row.get("latitude_degree"),
        "longitude": row.get("longitude_degree"),
        "country": row.get("country_sys_oterm_name"),
        "region": row.get("region"),
        "biome": row.get("biome_sys_oterm_name"),
    }


def get_strain_info(
    headers: Dict[str, str],
    strain_name: str,
    column_cache: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    if not strain_name:
        return None
    columns = get_table_columns(headers, "sdt_strain", column_cache)
    desired = [
        col for col in ["sdt_strain_name", "sdt_strain_description"] if col in columns
    ]
    row = select_first_row(
        headers,
        "sdt_strain",
        [{"column": "sdt_strain_name", "operator": "=", "value": strain_name}],
        desired,
    )
    if not row:
        return None
    return {
        "strain_name": row.get("sdt_strain_name") or strain_name,
        "description": row.get("sdt_strain_description"),
    }


def get_strain_id(
    headers: Dict[str, str],
    strain_name: str,
    column_cache: Dict[str, List[str]],
) -> Optional[str]:
    if not strain_name:
        return None
    columns = get_table_columns(headers, "sdt_strain", column_cache)
    if "sdt_strain_id" not in columns or "sdt_strain_name" not in columns:
        return None
    row = select_first_row(
        headers,
        "sdt_strain",
        [{"column": "sdt_strain_name", "operator": "=", "value": strain_name}],
        ["sdt_strain_id"],
    )
    return row.get("sdt_strain_id") if row else None


def build_downstream_lookup(
    out_lookup: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    downstream: Dict[str, List[Dict[str, Any]]] = {}
    for output_obj, processes in out_lookup.items():
        for proc in processes:
            for inp in proc.get("input_objs", []):
                downstream.setdefault(inp, []).append(
                    {
                        "output_obj": output_obj,
                        "process_term_name": proc.get("process_term_name"),
                        "protocol": proc.get("protocol"),
                        "date_end": proc.get("date_end"),
                        "id": proc.get("id"),
                    }
                )
    return downstream


def load_biosample_template_workbook(output_dir: str) -> Tuple[Path, Any, int, Dict[str, int]]:
    candidates = list(BIOSAMPLE_TEMPLATE_CANDIDATES)
    candidates.extend(
        [Path(output_dir) / "Microbe.1.0.xlsx", Path(output_dir) / "MIcrobe.1.0.xlsx"]
    )
    template_path = next((path for path in candidates if path.exists()), None)
    if not template_path:
        raise FileNotFoundError(
            "BioSample template not found. Expected Microbe.1.0.xlsx or MIcrobe.1.0.xlsx."
        )
    workbook = load_workbook(template_path)
    sheet = workbook.active

    header_row = None
    header_map: Dict[str, int] = {}
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row):
        for cell in row:
            if (cell.value or "").strip() == "*sample_name":
                header_row = cell.row
                for header_cell in sheet[header_row]:
                    header = header_cell.value
                    if header is None:
                        continue
                    header_str = str(header).strip()
                    if header_str:
                        header_map[header_str] = header_cell.column
                break
        if header_row is not None:
            break

    if header_row is None:
        raise ValueError(f"No header row found in BioSample template: {template_path}")

    return template_path, sheet, header_row, header_map


def load_sra_template_workbook(output_dir: str) -> Tuple[Path, Any, int, Dict[str, int]]:
    candidates = list(SRA_TEMPLATE_CANDIDATES)
    candidates.append(Path(output_dir) / "SRA_metadata.xlsx")
    template_path = next((path for path in candidates if path.exists()), None)
    if not template_path:
        raise FileNotFoundError(
            "SRA template not found. Expected SRA_metadata.xlsx."
        )
    workbook = load_workbook(template_path)
    sheet = workbook["SRA_data"] if "SRA_data" in workbook.sheetnames else workbook.active

    header_row = None
    header_map: Dict[str, int] = {}
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row):
        for cell in row:
            if (cell.value or "").strip() == "sample_name":
                header_row = cell.row
                for header_cell in sheet[header_row]:
                    header = header_cell.value
                    if header is None:
                        continue
                    header_str = str(header).strip()
                    if header_str:
                        header_map[header_str] = header_cell.column
                break
        if header_row is not None:
            break

    if header_row is None:
        raise ValueError(f"No header row found in SRA template: {template_path}")

    return template_path, sheet, header_row, header_map


def load_genome_template_workbook(output_dir: str) -> Tuple[Path, Any, int, Dict[str, int]]:
    candidates = list(GENOME_TEMPLATE_CANDIDATES)
    candidates.append(Path(output_dir) / "Template_GenomeBatch.xlsx")
    template_path = next((path for path in candidates if path.exists()), None)
    if not template_path:
        raise FileNotFoundError(
            "Genome template not found. Expected Template_GenomeBatch.xlsx."
        )
    workbook = load_workbook(template_path)
    sheet = workbook["Genome_data"] if "Genome_data" in workbook.sheetnames else workbook.active

    header_row = None
    header_map: Dict[str, int] = {}
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row):
        for cell in row:
            if (cell.value or "").strip().lower() == "biosample_accession":
                header_row = cell.row
                for header_cell in sheet[header_row]:
                    header = header_cell.value
                    if header is None:
                        continue
                    header_str = str(header).strip()
                    if header_str:
                        header_map[header_str] = header_cell.column
                break
        if header_row is not None:
            break

    if header_row is None:
        raise ValueError(f"No header row found in genome template: {template_path}")

    return template_path, sheet, header_row, header_map


def load_sra_instrument_models(workbook: Any) -> set[str]:
    sheet_name = "Library and Platform Terms"
    if sheet_name not in workbook.sheetnames:
        return set()
    sheet = workbook[sheet_name]
    platforms_row = None
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row):
        for cell in row:
            if (cell.value or "").strip() == "Platforms":
                platforms_row = cell.row
                break
        if platforms_row:
            break
    if not platforms_row:
        return set()
    platform_labels = {"ILLUMINA", "PACBIO_SMRT", "OXFORD_NANOPORE"}
    instrument_models: set[str] = set()
    for row in sheet.iter_rows(min_row=platforms_row + 1, max_row=sheet.max_row):
        for col_idx in (3, 7, 10):
            value = sheet.cell(row=row[0].row, column=col_idx).value
            if not value:
                continue
            value_str = str(value).strip()
            if not value_str or value_str in platform_labels:
                continue
            instrument_models.add(value_str)
    return instrument_models


def resolve_edr_path(link: str, edr_root: str) -> Optional[Path]:
    if not link or not link.startswith(EDR_URL_PREFIX):
        return None
    rel_path = link.replace(EDR_URL_PREFIX, "").lstrip("/")
    edr_root_path = Path(edr_root).resolve()
    return edr_root_path / rel_path


def link_fastq_files(
    genome_data: List[Dict[str, Any]],
    output_dir: str,
    edr_root: str,
    debug: bool = False,
) -> None:
    target_dir = Path(output_dir) / "reads_to_upload"
    target_dir.mkdir(parents=True, exist_ok=True)
    seen_targets: set[str] = set()
    link_count = 0
    for genome in genome_data:
        reads_list = genome.get("reads", []) or []
        for reads in reads_list:
            link = reads.get("link")
            if not link or ".fastq" not in link and ".fq" not in link:
                continue
            edr_path = resolve_edr_path(link, edr_root)
            if not edr_path:
                log_debug(f"Skipping non-EDR link: {link}", enabled=debug)
                continue
            filename = Path(link).name
            target = target_dir / filename
            if target.name in seen_targets:
                continue
            seen_targets.add(target.name)
            if target.exists() or target.is_symlink():
                continue
            try:
                os.symlink(edr_path, target)
                link_count += 1
            except FileExistsError:
                continue
    log_info(f"Symlinked {link_count} file(s) to {target_dir}")


def build_contig_link(genome: Dict[str, Any]) -> str:
    genome_link = genome.get("genome_link") or ""
    if not genome_link:
        return ""
    strain_name = (genome.get("strain") or {}).get("strain_name") or ""
    if strain_name:
        return f"{genome_link.rstrip('/')}/{strain_name}_contigs.fasta"
    return f"{genome_link.rstrip('/')}/contigs.fasta"


def select_contig_link_and_path(
    genome: Dict[str, Any],
    edr_root: str,
    debug: bool = False,
) -> Tuple[str, Optional[Path]]:
    link = build_contig_link(genome)
    if not link:
        return "", None
    edr_path = resolve_edr_path(link, edr_root)
    if not edr_path:
        return link, None
    filename = edr_path.name
    filtered_name = None
    if filename.endswith("_contigs.fasta"):
        filtered_name = filename.replace(
            "_contigs.fasta", "_coverage_filtered_contigs.fasta"
        )
    elif filename == "contigs.fasta":
        filtered_name = "contigs_filtered.fasta"
    if filtered_name:
        filtered_path = edr_path.with_name(filtered_name)
        if filtered_path.exists():
            edr_root_path = Path(edr_root).resolve()
            try:
                rel_path = filtered_path.resolve().relative_to(edr_root_path)
            except ValueError:
                log_debug(
                    f"Filtered contig path outside EDR root: {filtered_path}",
                    enabled=debug,
                )
                return link, edr_path
            filtered_link = f"{EDR_URL_PREFIX.rstrip('/')}/{rel_path.as_posix()}"
            return filtered_link, filtered_path
    return link, edr_path


def link_contig_files(
    genome_data: List[Dict[str, Any]],
    output_dir: str,
    edr_root: str,
    debug: bool = False,
) -> None:
    target_dir = Path(output_dir) / "contigs_to_upload"
    target_dir.mkdir(parents=True, exist_ok=True)
    seen_targets: set[str] = set()
    link_count = 0
    for genome in genome_data:
        link, edr_path = select_contig_link_and_path(
            genome, edr_root=edr_root, debug=debug
        )
        if not link or not link.endswith(".fasta"):
            continue
        if not edr_path:
            log_debug(f"Skipping non-EDR link: {link}", enabled=debug)
            continue
        filename = Path(link).name
        target = target_dir / filename
        if target.name in seen_targets:
            continue
        seen_targets.add(target.name)
        if target.exists() or target.is_symlink():
            continue
        try:
            os.symlink(edr_path, target)
            link_count += 1
        except FileExistsError:
            continue
    log_info(f"Symlinked {link_count} file(s) to {target_dir}")


def read_total_bases_from_reads_count(path: Path) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) == 2 and parts[0] == "total_bases":
                    return int(parts[1])
    except (OSError, ValueError):
        return None
    return None


def reads_count_path_from_reads_file(path: Path) -> Path:
    name = path.name
    for suffix in (".fastq.gz", ".fq.gz", ".fastq", ".fq"):
        if name.endswith(suffix):
            return path.with_name(name[: -len(suffix)] + "_reads_count.txt")
    return path.with_name(name + "_reads_count.txt")


def count_fasta_bases(path: Path) -> Optional[Tuple[int, int, int]]:
    total_chars = 0
    total_lines = 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(">"):
                    continue
                total_chars += len(line)
                total_lines += 1
    except OSError:
        return None
    total_bases = total_chars - total_lines
    return total_bases, total_chars, total_lines


def compute_coverage_from_files(
    genome: Dict[str, Any],
    edr_root: str,
    debug: bool = False,
) -> Optional[float]:
    contig_link, contig_path = select_contig_link_and_path(
        genome, edr_root=edr_root, debug=debug
    )
    if not contig_path or not contig_path.exists():
        log_debug(
            f"Coverage fallback: contig path missing for {contig_link}",
            enabled=debug,
        )
        return None
    contig_counts = count_fasta_bases(contig_path)
    if not contig_counts:
        log_debug(
            f"Coverage fallback: unable to read contigs at {contig_path}",
            enabled=debug,
        )
        return None
    contig_bases, contig_chars, contig_lines = contig_counts
    if contig_bases <= 0:
        log_debug(
            f"Coverage fallback: contigs bases <= 0 for {contig_path}",
            enabled=debug,
        )
        return None
    reads_total_bases = 0
    reads_files: List[str] = []
    for reads in genome.get("reads", []) or []:
        link = reads.get("link") or ""
        if not link or ".fastq" not in link and ".fq" not in link:
            continue
        edr_path = resolve_edr_path(link, edr_root)
        if not edr_path:
            continue
        count_path = reads_count_path_from_reads_file(edr_path)
        total_bases = read_total_bases_from_reads_count(count_path)
        if total_bases is None:
            continue
        reads_total_bases += total_bases
        reads_files.append(str(count_path))
    if reads_total_bases <= 0:
        log_debug(
            "Coverage fallback: no reads_count files found for coverage estimate.",
            enabled=debug,
        )
        return None
    coverage = reads_total_bases / contig_bases
    log_debug(
        "Coverage fallback: "
        f"reads_total_bases={reads_total_bases} "
        f"contig_bases={contig_bases} "
        f"(chars={contig_chars} lines={contig_lines}) "
        f"coverage={coverage:.4f} "
        f"reads_count_files={reads_files} "
        f"contigs_file={contig_path}",
        enabled=debug,
    )
    return coverage


def normalize_instrument_model(
    instrument_model: Optional[str],
    platform: Optional[str],
    allowed_instruments: set[str],
) -> str:
    if not instrument_model:
        return ""
    if not allowed_instruments:
        return instrument_model
    if instrument_model in allowed_instruments:
        return instrument_model

    lowered = instrument_model.strip().lower()
    allowed_lower = {inst.lower(): inst for inst in allowed_instruments}
    if lowered in allowed_lower:
        return allowed_lower[lowered]

    def strip_vendor(value: str) -> str:
        value = value.strip()
        for prefix in ("illumina ", "pacbio ", "oxford nanopore "):
            if value.lower().startswith(prefix):
                return value[len(prefix) :]
        return value

    stripped = strip_vendor(instrument_model).lower()
    for inst in allowed_instruments:
        if strip_vendor(inst).lower() == stripped:
            return inst

    if platform == "ILLUMINA" and "novaseq" in lowered:
        for candidate in ("Illumina NovaSeq 6000", "NovaSeq 6000"):
            if candidate in allowed_instruments:
                return candidate

    if platform == "ILLUMINA" and not lowered.startswith("illumina "):
        candidate = f"Illumina {instrument_model}"
        if candidate in allowed_instruments:
            return candidate
    if platform == "PACBIO_SMRT" and not lowered.startswith("pacbio "):
        candidate = f"PacBio {instrument_model}"
        if candidate in allowed_instruments:
            return candidate
    if platform == "OXFORD_NANOPORE" and not lowered.startswith("oxford nanopore "):
        candidate = f"Oxford Nanopore {instrument_model}"
        if candidate in allowed_instruments:
            return candidate

    return ""


def get_gtdb_genus_for_strain(
    headers: Dict[str, str],
    strain_name: Optional[str],
    column_cache: Dict[str, List[str]],
) -> Optional[str]:
    if not strain_name:
        return None
    table = "ddt_brick0000522"
    columns = get_table_columns(headers, table, column_cache)
    desired = [
        col
        for col in [
            "sdt_strain_name",
            "taxonomic_level_sys_oterm_name",
            "sdt_taxon_name",
        ]
        if col in columns
    ]
    if "sdt_strain_name" not in desired or "sdt_taxon_name" not in desired:
        return None
    try:
        rows = select_all_rows(
            headers,
            table,
            columns=desired,
            filters=[{"column": "sdt_strain_name", "operator": "=", "value": strain_name}],
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 504:
            log_info(f"GTDB genus query timed out for {strain_name}.")
            log_info(
                "Query payload: "
                + str(
                    {
                        "database": "enigma_coral",
                        "table": table,
                        "columns": [{"column": col} for col in desired],
                        "filters": [
                            {
                                "column": "sdt_strain_name",
                                "operator": "=",
                                "value": strain_name,
                            }
                        ],
                        "limit": 1000,
                        "offset": 0,
                    }
                )
            )
            raise
        raise
    genus = None
    for row in rows:
        level = (row.get("taxonomic_level_sys_oterm_name") or "").lower()
        if level == "genus":
            genus = row.get("sdt_taxon_name")
            break
    if not genus:
        return None
    if "_" in genus:
        genus = genus.split("_", 1)[0]
    return genus


def build_organism_name(genus: Optional[str], strain_name: Optional[str]) -> Optional[str]:
    if genus and strain_name:
        return f"{genus} sp. {strain_name}"
    if strain_name:
        return strain_name
    return None


def format_lat_lon(location: Dict[str, Any]) -> Optional[str]:
    lat = location.get("latitude")
    lon = location.get("longitude")
    if lat is None or lon is None:
        return None
    lat_dir = "N" if float(lat) >= 0 else "S"
    lon_dir = "E" if float(lon) >= 0 else "W"
    return f"{abs(float(lat))} {lat_dir} {abs(float(lon))} {lon_dir}"


def resolve_collected_by(
    start_token: str, out_lookup: Dict[str, List[Dict[str, Any]]]
) -> Optional[str]:
    visited: set[str] = set()

    def walk(obj_token: str) -> Optional[str]:
        if obj_token in visited:
            return None
        visited.add(obj_token)
        for proc in out_lookup.get(obj_token, []):
            process_name = (proc.get("process_term_name") or "").lower()
            person = (proc.get("person_term_name") or "").strip()
            if "sampling" in process_name and person:
                if "hazen lab" in person.lower():
                    return "Terry Hazen Lab, University of Tennessee, Knoxville, TN, USA"
                return person
            for inp in proc.get("input_objs", []):
                found = walk(inp)
                if found:
                    return found
        return None

    return walk(start_token)


def find_assembly_processes(
    genome_token: str, out_lookup: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    assembly_processes: List[Dict[str, Any]] = []
    visited_procs: set[str] = set()
    visited_objs: set[str] = set()

    def walk(obj: str) -> None:
        if obj in visited_objs:
            return
        visited_objs.add(obj)
        table_name, _ = parse_token(obj)
        for proc in out_lookup.get(obj, []):
            proc_id = proc.get("id")
            if proc_id in visited_procs:
                continue
            visited_procs.add(proc_id)
            process_name = (proc.get("process_term_name") or "").lower()
            if "assembly" in process_name or table_name == "sdt_assembly":
                assembly_processes.append(proc)
            for inp in proc.get("input_objs", []):
                walk(inp)

    walk(genome_token)
    return assembly_processes


def collect_protocols_from_processes(processes: Iterable[Dict[str, Any]]) -> List[str]:
    protocols: List[str] = []
    for proc in processes:
        protocols.extend(normalize_protocol_names(proc.get("protocol")))
    return sorted(set(protocols))


def infer_platform_from_protocols(
    protocol_names: Sequence[str],
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
) -> Tuple[Optional[str], Optional[str]]:
    platform = None
    instrument_model = None
    for name in protocol_names:
        info = get_protocol_info(headers, name, column_cache, protocol_cache)
        seq_tech = (info.get("sequencing_technology") or "").lower()
        machine_type = info.get("machine_type") or ""
        if "illumina" in seq_tech:
            platform = "ILLUMINA"
            instrument_model = machine_type or "Illumina NovaSeq 6000"
            break
        if "nanopore" in seq_tech or "ont" in seq_tech:
            platform = "OXFORD_NANOPORE"
            instrument_model = machine_type or "PromethION"
            break
        if "pacbio" in seq_tech:
            platform = "PACBIO_SMRT"
            instrument_model = machine_type or "PacBio Sequel"
            break
    return platform, instrument_model


def infer_assembly_method_from_protocols(
    protocol_names: Sequence[str],
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
) -> Optional[str]:
    for name in protocol_names:
        info = get_protocol_info(headers, name, column_cache, protocol_cache)
        desc = (info.get("protocol_description") or "").lower()
        proto_name = (info.get("protocol_name") or name).lower()
        text = f"{proto_name} {desc}"
        if "spades" in text:
            version_match = re.search(r"spades\s+v?(\d+\.\d+\.\d+)", text)
            return f"SPAdes {version_match.group(1)}" if version_match else "SPAdes"
        if "flye" in text:
            version_match = re.search(r"flye\s+v?(\d+\.\d+)", text)
            return f"Flye {version_match.group(1)}" if version_match else "Flye"
        if "canu" in text:
            version_match = re.search(r"canu\s+v?(\d+\.\d+)", text)
            return f"CANU {version_match.group(1)}" if version_match else "CANU"
        if "metaspades" in text:
            return "MetaSPAdes"
        if "unicycler" in text:
            return "Unicycler"
    return None


def split_assembly_method(method: Optional[str], debug: bool = False) -> Tuple[str, str]:
    if not method:
        return "", ""
    text = method.strip()
    match = re.search(r"(?:v\.?\s*)?(\d+(?:\.\d+){1,3})", text, re.IGNORECASE)
    if not match:
        if debug:
            log_debug(
                f"Assembly method parse: raw={method!r} -> method={text!r} version=''",
                enabled=debug,
            )
        return text, ""
    version = match.group(1)
    name = (text[: match.start()] + text[match.end() :]).strip(" -_()")
    if not name:
        name = text.strip()
    if debug:
        log_debug(
            f"Assembly method parse: raw={method!r} -> method={name!r} version={version!r}",
            enabled=debug,
        )
    return name, version


def choose_assembly_date(processes: Iterable[Dict[str, Any]]) -> str:
    dates = [proc.get("date_end") for proc in processes if proc.get("date_end")]
    if not dates:
        return ""
    return sorted(dates)[-1]


def normalize_strain_name(genome_name: str, strain: Optional[Dict[str, Any]]) -> str:
    if strain and strain.get("strain_name"):
        return str(strain.get("strain_name"))
    if genome_name:
        return genome_name.split(".", 1)[0]
    return ""


def fetch_read_coverage_map(
    headers: Dict[str, str],
    strain_names: Sequence[str],
    column_cache: Dict[str, List[str]],
) -> Dict[str, float]:
    if not strain_names:
        return {}
    columns = get_table_columns(headers, READ_COVERAGE_TABLE, column_cache)
    if "sdt_strain_name" not in columns or READ_COVERAGE_COLUMN not in columns:
        return {}
    rows = select_all_rows(
        headers,
        READ_COVERAGE_TABLE,
        columns=["sdt_strain_name", READ_COVERAGE_COLUMN],
        filters=None,
        limit=1000,
    )
    coverage_values: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        strain = row.get("sdt_strain_name")
        value = row.get(READ_COVERAGE_COLUMN)
        if strain is None or value is None:
            continue
        if strain_names and str(strain) not in strain_names:
            continue
        try:
            coverage_values[str(strain)].append(float(value))
        except (TypeError, ValueError):
            continue
    coverage_map: Dict[str, float] = {}
    for strain, values in coverage_values.items():
        if values:
            coverage_map[strain] = sum(values) / len(values)
    return coverage_map


def infer_sequencing_techs(
    protocol_names: Sequence[str],
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
) -> List[str]:
    techs: set[str] = set()
    for name in protocol_names:
        info = get_protocol_info(headers, name, column_cache, protocol_cache)
        tech = info.get("sequencing_technology")
        if tech:
            techs.add(tech)
    return sorted(techs)


def infer_isolation_source(sample_name: str, sample: Dict[str, Any]) -> Optional[str]:
    material = sample.get("material_name") or ""
    description = sample.get("description") or ""
    text = " ".join(part for part in [material, description, sample_name] if part).lower()
    if (
        "groundwater" in text
        or re.search(r"\bground\s*water\b", text)
        or "subsurface water" in text
        or "aquifer" in text
    ):
        return f"Groundwater sample {sample_name} from ORR".strip()
    if (
        re.search(r"\bsoil\b", text)
        or "topsoil" in text
        or "subsoil" in text
        or "rhizosphere" in text
        or "sediment" in text
    ):
        if "sediment" in text:
            return f"Sediment sample {sample_name} from ORR".strip()
        return f"Soil sample {sample_name} from ORR".strip()
    return None


def format_depth_meters(depth_value: Any) -> str:
    if depth_value in (None, ""):
        return ""
    try:
        depth_float = float(depth_value)
    except (TypeError, ValueError):
        depth_str = str(depth_value).strip()
        if not depth_str:
            return ""
        return f"{depth_str} m"
    if depth_float.is_integer():
        depth_str = str(int(depth_float))
    else:
        depth_str = str(depth_float)
    return f"{depth_str} m"


def build_biosample_name(sample_name: str, strain_name: str) -> str:
    formatted = f"environmental sample {sample_name} isolate {strain_name}".strip()
    return formatted


def extract_date_from_filenames(*filenames: Optional[str]) -> Optional[str]:
    for filename in filenames:
        if not filename:
            continue
        match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
        if match:
            return match.group(0)
    return None


def infer_read_tech_label(platform: Optional[str], sequencing_tech: Optional[str]) -> str:
    platform_upper = (platform or "").upper()
    seq_lower = (sequencing_tech or "").lower()
    if "PACBIO" in platform_upper or "pacbio" in seq_lower:
        return "Pacbio"
    if "NANOPORE" in platform_upper or "nanopore" in seq_lower or "ont" in seq_lower:
        return "Nanopore"
    return "Illumina"


def is_long_read_tech(platform: Optional[str], sequencing_tech: Optional[str]) -> bool:
    platform_upper = (platform or "").upper()
    seq_lower = (sequencing_tech or "").lower()
    return bool(
        "PACBIO" in platform_upper
        or "NANOPORE" in platform_upper
        or "pacbio" in seq_lower
        or "nanopore" in seq_lower
        or "ont" in seq_lower
    )


def generate_biosample_table(
    genome_data: List[Dict[str, Any]],
    output_file: str,
    output_dir: str,
    debug: bool = False,
) -> None:
    template_path, sheet, header_row, header_map = load_biosample_template_workbook(
        output_dir
    )

    last_data_row = header_row
    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        if any(cell.value not in (None, "") for cell in row):
            last_data_row = row[0].row

    next_row = last_data_row + 1
    for genome in genome_data:
        sample = genome.get("sample", {}) or {}
        location = genome.get("location", {}) or {}
        strain = genome.get("strain", {}) or {}

        sample_name = sample.get("sample_name") or ""
        strain_name = strain.get("strain_name") or sample.get("sample_name")
        formatted_sample_name = build_biosample_name(sample_name, strain_name)
        genus = genome.get("gtdb_genus")
        organism_name = build_organism_name(genus, strain_name)

        isolation_source = infer_isolation_source(sample_name, sample)
        if debug:
            log_debug(
                "Biosample isolation_source debug: "
                f"sample_name={sample_name!r} "
                f"material_name={(sample.get('material_name') or '')!r} "
                f"description={(sample.get('description') or '')!r} "
                f"resolved={isolation_source!r}",
                enabled=True,
            )

        values = {
            "*sample_name": formatted_sample_name,
            "*organism": organism_name or "",
            "strain": strain_name or "",
            "isolate": "",
            "host": "",
            "isolation_source": isolation_source or "",
            "*collection_date": sample.get("date") or "",
            "*geo_loc_name": "USA: Tennessee, Oak Ridge Reservation (ORR)",
            "*sample_type": "cell culture",
            "collected_by": genome.get("collected_by") or "",
            "depth": format_depth_meters(sample.get("depth_meter")),
            "env_broad_scale": "temperate woodland biome [ENVO:01000221]",
            "lat_lon": format_lat_lon(location) or "",
        }

        for header, value in values.items():
            col = header_map.get(header)
            if col is not None:
                sheet.cell(row=next_row, column=col, value=value)
        next_row += 1

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.parent.save(output_path)


def generate_sra_table(
    genome_data: List[Dict[str, Any]],
    output_file: str,
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
    debug: bool = False,
) -> None:
    template_path, sheet, header_row, header_map = load_sra_template_workbook(
        Path(output_file).parent
    )
    allowed_instruments = load_sra_instrument_models(sheet.parent)
    if debug:
        log_debug(
            "SRA template headers: "
            f"platform_col={header_map.get('platform')} "
            f"instrument_model_col={header_map.get('instrument_model')} "
            f"allowed_instruments={len(allowed_instruments)}",
            enabled=True,
        )

    last_data_row = header_row
    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        if any(cell.value not in (None, "") for cell in row):
            last_data_row = row[0].row

    next_row = last_data_row + 1
    used_library_ids: Dict[str, int] = {}
    used_titles: Dict[str, int] = {}
    short_read_date_flag: Dict[str, bool] = {}
    short_read_dates: Dict[str, List[Optional[str]]] = {}
    for genome in genome_data:
        strain = genome.get("strain", {}) or {}
        sample = genome.get("sample", {}) or {}
        sample_name = sample.get("sample_name") or ""
        isolate_name = strain.get("strain_name") or sample.get("sample_name") or genome.get(
            "genome_name", ""
        )
        biosample_name = build_biosample_name(sample_name, isolate_name)
        reads_list = genome.get("reads", []) or []

        reads_by_base_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for reads in reads_list:
            reads_name = reads.get("reads_name", "") or ""
            base_name = re.sub(
                r"[_-](R[12]|fwd|rev|forward|reverse|paired|unpaired).*$",
                "",
                reads_name,
                flags=re.IGNORECASE,
            )
            reads_by_base_name[base_name].append(reads)

        for base_name, reads_group in reads_by_base_name.items():
            if len(reads_group) >= 2:
                library_layout = "PAIRED"
                forward_reads = None
                reverse_reads = None
                for reads in reads_group:
                    name_lower = (reads.get("reads_name") or "").lower()
                    if any(
                        x in name_lower
                        for x in ["_r1", "_fwd", "_forward", "_1.fastq", "_1.fq"]
                    ):
                        forward_reads = reads
                    elif any(
                        x in name_lower
                        for x in ["_r2", "_rev", "_reverse", "_2.fastq", "_2.fq"]
                    ):
                        reverse_reads = reads
                if not forward_reads:
                    forward_reads = reads_group[0]
                if not reverse_reads and len(reads_group) > 1:
                    reverse_reads = reads_group[1]
                filename = (forward_reads.get("link") or "").split("/")[-1]
                filename2 = (reverse_reads.get("link") or "").split("/")[-1]
                primary_reads = forward_reads
            else:
                primary_reads = reads_group[0] if reads_group else None
                filename = (
                    (primary_reads.get("link") or "").split("/")[-1]
                    if primary_reads
                    else ""
                )
                filename2 = None
                if primary_reads and is_paired_read_type(primary_reads.get("read_type")):
                    library_layout = "PAIRED"
                else:
                    library_layout = "SINGLE"

            if not primary_reads:
                continue

            source_protocols = primary_reads.get("source_protocols", []) or []
            seq_tech_debug = (
                primary_reads.get("source_sequencing_technology")
                or primary_reads.get("sequencing_technology")
                or ""
            )
            if source_protocols:
                protocol_names = list(source_protocols)
            else:
                protocol_names = []
                protocol_names.extend(normalize_protocol_names(sample.get("protocol")))
                protocol_names.extend(primary_reads.get("protocols", []))
                if not protocol_names:
                    assembly_protocols = collect_protocols_from_processes(
                        genome.get("assembly_processes", []) or []
                    )
                    protocol_names.extend(assembly_protocols)
            platform, instrument_model = infer_platform_from_protocols(
                protocol_names, headers, column_cache, protocol_cache
            )

            if not platform:
                seq_tech = (
                    primary_reads.get("source_sequencing_technology")
                    or primary_reads.get("sequencing_technology")
                    or ""
                ).lower()
                if "illumina" in seq_tech:
                    platform = "ILLUMINA"
                    instrument_model = "unknown"
                elif "nanopore" in seq_tech or "ont" in seq_tech:
                    platform = "OXFORD_NANOPORE"
                    instrument_model = "unknown"
                elif "pacbio" in seq_tech:
                    platform = "PACBIO_SMRT"
                    instrument_model = "unknown"
                else:
                    platform = "ILLUMINA"
                    instrument_model = "unknown"

            if debug:
                log_debug(
                    "SRA instrument debug: "
                    f"sample={biosample_name!r} "
                    f"reads={primary_reads.get('reads_name')!r} "
                    f"source_reads={primary_reads.get('source_reads_token')!r} "
                    f"source_protocols={source_protocols!r} "
                    f"protocol_names={protocol_names!r} "
                    f"seq_tech={seq_tech_debug!r} "
                    f"platform={platform!r} "
                    f"instrument_model={instrument_model!r}",
                    enabled=True,
                )

            instrument_model = normalize_instrument_model(
                instrument_model if instrument_model != "unknown" else "",
                platform,
                allowed_instruments,
            )
            if debug and instrument_model == "":
                log_debug(
                    "SRA instrument filtered: "
                    f"instrument_model not in template list",
                    enabled=True,
                )

            seq_tech = (
                primary_reads.get("source_sequencing_technology")
                or primary_reads.get("sequencing_technology")
            )
            tech_label = infer_read_tech_label(platform, seq_tech)
            long_read = is_long_read_tech(platform, seq_tech)
            reads_date = extract_date_from_filenames(filename, filename2)

            if not long_read:
                short_read_dates.setdefault(isolate_name, []).append(reads_date)

    for isolate_name, dates in short_read_dates.items():
        if len(dates) > 1 and any(date for date in dates):
            short_read_date_flag[isolate_name] = True

    for genome in genome_data:
        strain = genome.get("strain", {}) or {}
        sample = genome.get("sample", {}) or {}
        sample_name = sample.get("sample_name") or ""
        isolate_name = strain.get("strain_name") or sample.get("sample_name") or genome.get(
            "genome_name", ""
        )
        biosample_name = build_biosample_name(sample_name, isolate_name)
        reads_list = genome.get("reads", []) or []

        reads_by_base_name = defaultdict(list)
        for reads in reads_list:
            reads_name = reads.get("reads_name", "") or ""
            base_name = re.sub(
                r"[_-](R[12]|fwd|rev|forward|reverse|paired|unpaired).*$",
                "",
                reads_name,
                flags=re.IGNORECASE,
            )
            reads_by_base_name[base_name].append(reads)

        for base_name, reads_group in reads_by_base_name.items():
            if len(reads_group) >= 2:
                library_layout = "PAIRED"
                forward_reads = None
                reverse_reads = None
                for reads in reads_group:
                    name_lower = (reads.get("reads_name") or "").lower()
                    if any(
                        x in name_lower
                        for x in ["_r1", "_fwd", "_forward", "_1.fastq", "_1.fq"]
                    ):
                        forward_reads = reads
                    elif any(
                        x in name_lower
                        for x in ["_r2", "_rev", "_reverse", "_2.fastq", "_2.fq"]
                    ):
                        reverse_reads = reads
                if not forward_reads:
                    forward_reads = reads_group[0]
                if not reverse_reads and len(reads_group) > 1:
                    reverse_reads = reads_group[1]
                filename = (forward_reads.get("link") or "").split("/")[-1]
                filename2 = (reverse_reads.get("link") or "").split("/")[-1]
                primary_reads = forward_reads
            else:
                primary_reads = reads_group[0] if reads_group else None
                filename = (
                    (primary_reads.get("link") or "").split("/")[-1]
                    if primary_reads
                    else ""
                )
                filename2 = None
                if primary_reads and is_paired_read_type(primary_reads.get("read_type")):
                    library_layout = "PAIRED"
                else:
                    library_layout = "SINGLE"

            if not primary_reads:
                continue

            source_protocols = primary_reads.get("source_protocols", []) or []
            seq_tech_debug = (
                primary_reads.get("source_sequencing_technology")
                or primary_reads.get("sequencing_technology")
                or ""
            )
            if source_protocols:
                protocol_names = list(source_protocols)
            else:
                protocol_names = []
                protocol_names.extend(normalize_protocol_names(sample.get("protocol")))
                protocol_names.extend(primary_reads.get("protocols", []))
                if not protocol_names:
                    assembly_protocols = collect_protocols_from_processes(
                        genome.get("assembly_processes", []) or []
                    )
                    protocol_names.extend(assembly_protocols)
            platform, instrument_model = infer_platform_from_protocols(
                protocol_names, headers, column_cache, protocol_cache
            )

            if not platform:
                seq_tech = (
                    primary_reads.get("source_sequencing_technology")
                    or primary_reads.get("sequencing_technology")
                    or ""
                ).lower()
                if "illumina" in seq_tech:
                    platform = "ILLUMINA"
                    instrument_model = "unknown"
                elif "nanopore" in seq_tech or "ont" in seq_tech:
                    platform = "OXFORD_NANOPORE"
                    instrument_model = "unknown"
                elif "pacbio" in seq_tech:
                    platform = "PACBIO_SMRT"
                    instrument_model = "unknown"
                else:
                    platform = "ILLUMINA"
                    instrument_model = "unknown"

            if debug:
                log_debug(
                    "SRA instrument debug: "
                    f"sample={biosample_name!r} "
                    f"reads={primary_reads.get('reads_name')!r} "
                    f"source_reads={primary_reads.get('source_reads_token')!r} "
                    f"source_protocols={source_protocols!r} "
                    f"protocol_names={protocol_names!r} "
                    f"seq_tech={seq_tech_debug!r} "
                    f"platform={platform!r} "
                    f"instrument_model={instrument_model!r}",
                    enabled=True,
                )

            instrument_model = normalize_instrument_model(
                instrument_model if instrument_model != "unknown" else "",
                platform,
                allowed_instruments,
            )
            if debug and instrument_model == "":
                log_debug(
                    "SRA instrument filtered: "
                    f"instrument_model not in template list",
                    enabled=True,
                )

            seq_tech = (
                primary_reads.get("source_sequencing_technology")
                or primary_reads.get("sequencing_technology")
            )
            tech_label = infer_read_tech_label(platform, seq_tech)
            long_read = is_long_read_tech(platform, seq_tech)
            reads_date = extract_date_from_filenames(filename, filename2)

            if long_read:
                if tech_label == "Pacbio":
                    base_library_id = f"{isolate_name}_pacbio"
                else:
                    base_library_id = f"{isolate_name}_nano"
            else:
                base_library_id = isolate_name

            library_id = base_library_id
            if (
                not long_read
                and short_read_date_flag.get(isolate_name)
                and reads_date
            ):
                library_id = f"{base_library_id}_{reads_date}"
            if library_id in used_library_ids and reads_date:
                library_id = f"{base_library_id}_{reads_date}"
            if library_id in used_library_ids:
                suffix = used_library_ids[library_id] + 1
                library_id = f"{library_id}_{suffix}"
            used_library_ids[library_id] = used_library_ids.get(library_id, 0) + 1

            title = f"{tech_label} reads for {isolate_name}"
            if (
                not long_read
                and short_read_date_flag.get(isolate_name)
                and reads_date
            ):
                title = f"{title}, {reads_date}"
            elif title in used_titles and reads_date:
                title = f"{title}, {reads_date}"
            if title in used_titles:
                suffix = used_titles[title] + 1
                title = f"{title}, {suffix}"
            used_titles[title] = used_titles.get(title, 0) + 1

            values = {
                "sample_name": biosample_name,
                "library_ID": library_id,
                "title": title,
                "library_strategy": "WGS",
                "library_source": "GENOMIC",
                "library_selection": "RANDOM",
                "library_layout": library_layout,
                "platform": platform,
                "instrument_model": instrument_model,
                "design_description": "Whole genome shotgun sequencing for isolate characterization.",
                "filetype": "fastq",
                "filename": filename,
            }
            if filename2:
                values["filename2"] = filename2

            for header, value in values.items():
                col = header_map.get(header)
                if col is not None:
                    sheet.cell(row=next_row, column=col, value=value)
            next_row += 1

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.parent.save(output_path)


def generate_genome_table(
    genome_data: List[Dict[str, Any]],
    output_file: str,
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
    edr_root: str,
    debug: bool = False,
) -> None:
    template_path, sheet, header_row, header_map = load_genome_template_workbook(
        Path(output_file).parent
    )

    last_data_row = header_row
    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        if any(cell.value not in (None, "") for cell in row):
            last_data_row = row[0].row

    next_row = last_data_row + 1
    for genome in genome_data:
        strain = genome.get("strain", {}) or {}
        sample = genome.get("sample", {}) or {}
        raw_sample_name = sample.get("sample_name") or ""
        isolate_name = strain.get("strain_name") or raw_sample_name or genome.get(
            "genome_name", ""
        )
        if not raw_sample_name:
            raw_sample_name = isolate_name
        biosample_name = build_biosample_name(raw_sample_name, isolate_name)

        assembly_protocols = collect_protocols_from_processes(
            genome.get("assembly_processes", []) or []
        )
        assembly_method = infer_assembly_method_from_protocols(
            assembly_protocols, headers, column_cache, protocol_cache
        )
        method_name, method_version = split_assembly_method(assembly_method, debug=debug)
        if not method_name:
            method_name = "unknown"
        if not method_version:
            method_version = "unknown"

        seq_techs = infer_sequencing_techs(
            assembly_protocols, headers, column_cache, protocol_cache
        )
        if not seq_techs:
            for reads in genome.get("reads", []) or []:
                tech = reads.get("sequencing_technology")
                if tech:
                    seq_techs.append(tech)
        sequencing_technology = "; ".join(sorted(set(seq_techs))) if seq_techs else ""

        fasta_link, _ = select_contig_link_and_path(
            genome, edr_root=edr_root, debug=debug
        )
        fasta_filename = Path(fasta_link).name if fasta_link else ""
        assembly_date = choose_assembly_date(genome.get("assembly_processes", []) or [])

        values = {
            "biosample_accession": "",
            "sample_name": biosample_name,
            "assembly_date": assembly_date,
            "assembly_name": genome.get("genome_name", ""),
            "assembly_method": method_name,
            "assembly_method_version": method_version,
            "genome_coverage": genome.get("genome_coverage", ""),
            "sequencing_technology": sequencing_technology,
            "reference_genome": "",
            "update_for": "",
            "bacteria_available_from": Bacteria_AVAILABLE_FROM,
            "filename": fasta_filename,
        }

        for header, value in values.items():
            col = header_map.get(header)
            if col is not None:
                sheet.cell(row=next_row, column=col, value=value)
        next_row += 1

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.parent.save(output_path)


def process_genomes_for_submission(
    headers: Dict[str, str],
    genome_names: Sequence[str],
    output_dir: str = DEFAULT_OUTPUT_DIR,
    debug: bool = False,
    edr_path: str = DEFAULT_EDR_PATH,
) -> List[Dict[str, Any]]:
    if debug:
        set_debug(True)
        log_info("Debug enabled; BERDL API calls will be logged")
    os.makedirs(output_dir, exist_ok=True)
    column_cache: Dict[str, List[str]] = {}
    protocol_cache: Dict[str, Dict[str, Optional[str]]] = {}
    read_cache: Dict[str, Dict[str, Any]] = {}

    log_info(f"Preparing BERDL provenance data for {len(genome_names)} genome(s)")
    log_info("Discovering tables in BERDL")
    discovered_tables = discover_tables(headers)
    log_info(f"Discovered {len(discovered_tables)} BERDL tables")
    log_info("Loading sys_process cache (may take a while)")
    cache = load_process_cache(headers, discovered_tables)
    log_info(f"Loaded {len(cache.process_rows)} sys_process rows")
    downstream_lookup = build_downstream_lookup(cache.out_lookup)
    resolver = NameResolver(headers) if debug else None

    log_info("Fetching genome table schema")
    genome_columns = get_table_columns(headers, "sdt_genome", column_cache)
    genome_desired = [
        col
        for col in ["sdt_genome_id", "sdt_genome_name", "sdt_strain_name", "link"]
        if col in genome_columns
    ]

    genome_data: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, genome_name in enumerate(genome_names, start=1):
        log_info(f"[{idx}/{len(genome_names)}] Processing genome {genome_name}")
        genome_row = select_first_row(
            headers,
            "sdt_genome",
            [{"column": "sdt_genome_name", "operator": "=", "value": genome_name}],
            genome_desired,
        )
        if not genome_row:
            warnings.append(f"Genome {genome_name} not found in sdt_genome table")
            continue

        genome_id = genome_row.get("sdt_genome_id")
        if not genome_id:
            warnings.append(f"Genome {genome_name} missing sdt_genome_id")
            continue

        genome_token = f"sdt_genome:{genome_id}"
        strain_name = genome_row.get("sdt_strain_name")
        genome_link = genome_row.get("link")
        log_debug(
            f"Genome token={genome_token} strain={strain_name} link={genome_link}",
            enabled=debug,
        )

        if debug:
            log_info(f"Provenance for {genome_name} ({genome_token})")
            walk_provenance(genome_token, cache.out_lookup, resolver)  # type: ignore[arg-type]
        log_info(f"Finding reads for {genome_name}")
        strain_token = None
        if strain_name:
            strain_id = get_strain_id(headers, strain_name, column_cache)
            if strain_id:
                strain_token = f"sdt_strain:{strain_id}"
        reads_list = find_oldest_reads_with_fastq(
            genome_token,
            cache.out_lookup,
            downstream_lookup,
            headers,
            column_cache,
            read_cache,
            strain_token=strain_token,
            log_label=f"[reads {genome_name}] ",
        )
        if not reads_list:
            warnings.append(
                f"Genome {genome_name}: No reads with FASTQ files on {FASTQ_HOST} found"
            )
        log_info(f"Found {len(reads_list)} read set(s) with FASTQ for {genome_name}")

        log_info(f"Finding samples for {genome_name}")
        samples_list = find_samples_from_genome(
            genome_token, cache.out_lookup, headers, column_cache
        )
        log_info(f"Found {len(samples_list)} sample(s) for {genome_name}")
        sample_data = samples_list[0] if samples_list else None
        location_data = None
        if sample_data and sample_data.get("location_name"):
            log_info(f"Resolving location {sample_data['location_name']}")
            location_data = get_location_info(
                headers, sample_data["location_name"], column_cache
            )

        if strain_name:
            log_info(f"Resolving strain {strain_name}")
        strain_data = get_strain_info(headers, strain_name, column_cache) if strain_name else None
        gtdb_genus = get_gtdb_genus_for_strain(headers, strain_name, column_cache)
        collected_by = None
        if sample_data and sample_data.get("sample_token"):
            collected_by = resolve_collected_by(sample_data["sample_token"], cache.out_lookup)
        if collected_by is None:
            collected_by = resolve_collected_by(genome_token, cache.out_lookup)

        log_info(f"Finding assembly processes for {genome_name}")
        assembly_processes = find_assembly_processes(genome_token, cache.out_lookup)
        log_info(f"Found {len(assembly_processes)} assembly process(es) for {genome_name}")

        genome_data.append(
            {
                "genome_name": genome_name,
                "genome_id": genome_id,
                "genome_link": genome_link,
                "strain": strain_data or {"strain_name": strain_name},
                "sample": sample_data,
                "location": location_data,
                "reads": reads_list,
                "assembly_processes": assembly_processes,
                "gtdb_genus": gtdb_genus,
                "collected_by": collected_by,
            }
        )

    if warnings:
        log_info("Warnings:")
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)

    log_info("Fetching read coverage data")
    strain_names = [
        normalize_strain_name(genome.get("genome_name", ""), genome.get("strain"))
        for genome in genome_data
    ]
    strain_names = [name for name in strain_names if name]
    coverage_map = fetch_read_coverage_map(headers, strain_names, column_cache)
    for genome in genome_data:
        strain_name = normalize_strain_name(genome.get("genome_name", ""), genome.get("strain"))
        if strain_name in coverage_map:
            genome["genome_coverage"] = coverage_map[strain_name]
        else:
            coverage = compute_coverage_from_files(genome, edr_path, debug=debug)
            if coverage is not None:
                genome["genome_coverage"] = coverage

    log_info("Writing biosample table")
    generate_biosample_table(
        genome_data,
        os.path.join(output_dir, "biosample_table_Microbe.1.0.xlsx"),
        output_dir,
        debug=debug,
    )
    log_info("Writing SRA metadata table")
    generate_sra_table(
        genome_data,
        os.path.join(output_dir, "sra_table_SRA_metadata.xlsx"),
        headers,
        column_cache,
        protocol_cache,
        debug=debug,
    )
    log_info("Writing genome metadata table")
    generate_genome_table(
        genome_data,
        os.path.join(output_dir, "genome_table_Template_GenomeBatch.xlsx"),
        headers,
        column_cache,
        protocol_cache,
        edr_root=edr_path,
        debug=debug,
    )
    log_info("Linking FASTQ files for upload")
    link_fastq_files(genome_data, output_dir, edr_path, debug=debug)
    log_info("Linking contig files for upload")
    link_contig_files(genome_data, output_dir, edr_path, debug=debug)

    print("Generated submission tables:")
    print(f"  - {os.path.join(output_dir, 'biosample_table_Microbe.1.0.xlsx')}")
    print(f"  - {os.path.join(output_dir, 'sra_table_SRA_metadata.xlsx')}")
    print(f"  - {os.path.join(output_dir, 'genome_table_Template_GenomeBatch.xlsx')}")

    return genome_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate NCBI submission tables using BERDL provenance data."
    )
    parser.add_argument(
        "--genome-name",
        action="append",
        dest="genome_names",
        help="Genome name from sdt_genome.sdt_genome_name (repeatable).",
    )
    parser.add_argument(
        "--genome-list",
        help="Path to a file with one genome name per line.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write output files (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL),
        help=f"MCP base URL (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging, including BERDL API calls.",
    )
    parser.add_argument(
        "--edr-path",
        default=DEFAULT_EDR_PATH,
        help=f"Path to ENIGMA data repository root (default: {DEFAULT_EDR_PATH}).",
    )
    return parser.parse_args()


def load_genome_names(args: argparse.Namespace) -> List[str]:
    names = list(args.genome_names or [])
    if args.genome_list:
        with open(args.genome_list, "r", encoding="utf-8") as handle:
            for line in handle:
                name = line.strip()
                if name:
                    names.append(name)
    deduped = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def main() -> None:
    args = parse_args()
    walk_provenance_module.BASE_URL = args.base_url
    enable_request_failure_logging()
    genome_names = load_genome_names(args)
    if not genome_names:
        raise SystemExit("No genomes provided. Use --genome-name or --genome-list.")
    headers = get_headers()
    process_genomes_for_submission(
        headers,
        genome_names,
        output_dir=args.output_dir,
        debug=args.debug,
        edr_path=args.edr_path,
    )


if __name__ == "__main__":
    main()
