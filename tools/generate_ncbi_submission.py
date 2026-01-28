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
import csv
import os
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pathlib import Path
import sys
from openpyxl import load_workbook

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


FASTQ_HOST = "genomics.lbl.gov"
DEFAULT_OUTPUT_DIR = "ncbi_submission"
PROTOCOL_TABLE = "sdt_protocol"
BIOSAMPLE_TEMPLATE_CANDIDATES = [
    Path("ncbi_submission") / "Microbe.1.0.xlsx",
    Path("ncbi_submission") / "MIcrobe.1.0.xlsx",
    Path("genome_upload") / "ncbi_submission" / "Microbe.1.0.xlsx",
]


def log_info(message: str) -> None:
    print(f"[info] {message}", file=sys.stderr)


def log_debug(message: str, enabled: bool) -> None:
    if enabled:
        print(f"[debug] {message}", file=sys.stderr)


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

    def collect_reads_upstream(start_token: str) -> List[Dict[str, Any]]:
        visited: set[str] = set()
        reads_candidates: List[Dict[str, Any]] = []

        def walk_upstream(
            obj_token: str, depth: int = 0, path: Optional[List[str]] = None
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
                    protocols = []
                    for proc in out_lookup.get(obj_token, []):
                        protocols.extend(normalize_protocol_names(proc.get("protocol")))
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
                        }
                    )

            proc_list = out_lookup.get(obj_token, [])
            for proc in proc_list:
                process_name = (proc.get("process_term_name") or "").lower()
                if table_name in ["sdt_assembly", "sdt_genome"]:
                    for inp in proc.get("input_objs", []):
                        walk_upstream(inp, depth + 1, current_path)
                elif table_name == "sdt_reads":
                    if "reads processing" in process_name or "copy data" in process_name:
                        for inp in proc.get("input_objs", []):
                            walk_upstream(inp, depth + 1, current_path)
                else:
                    for inp in proc.get("input_objs", []):
                        inp_table, _ = parse_token(inp)
                        if inp_table in ["sdt_reads", "sdt_assembly"]:
                            walk_upstream(inp, depth + 1, current_path)

        walk_upstream(start_token)
        return reads_candidates

    def collect_reads_downstream(start_token: str) -> List[Dict[str, Any]]:
        visited: set[str] = set()
        reads_candidates: List[Dict[str, Any]] = []

        def walk_downstream(
            obj_token: str, depth: int = 0, path: Optional[List[str]] = None
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
                    protocols = []
                    for proc in out_lookup.get(obj_token, []):
                        protocols.extend(normalize_protocol_names(proc.get("protocol")))
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
                        }
                    )

            for proc in downstream_lookup.get(obj_token, []):
                out_token = proc.get("output_obj")
                if out_token:
                    walk_downstream(out_token, depth + 1, current_path)

        walk_downstream(start_token)
        return reads_candidates

    def select_most_ancestral(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        oldest_reads: List[Dict[str, Any]] = []
        for reads in candidates:
            reads_token = reads["reads_token"]
            path = reads["path"]
            is_oldest = True
            for other_reads in candidates:
                other_token = other_reads["reads_token"]
                if other_token == reads_token:
                    continue
                if other_token in path:
                    is_oldest = False
                    break
            if is_oldest:
                oldest_reads.append(reads)
        return oldest_reads

    def log_reads(message: str, reads_list: List[Dict[str, Any]]) -> None:
        prefix = log_label or ""
        if not reads_list:
            log_info(f"{prefix}{message}: none")
            return
        details = ", ".join(
            f"{r.get('reads_id')}:{r.get('reads_name')}" for r in reads_list
        )
        log_info(f"{prefix}{message}: {details}")

    def select_preferred_reads(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        original_candidates = candidates
        copy_candidates = [c for c in candidates if c.get("produced_by_copy_data")]
        if copy_candidates:
            log_reads("Reads produced by copy data", copy_candidates)
        raw_candidates = [c for c in candidates if not c.get("processed_by_trim")]
        if raw_candidates:
            removed = [c for c in candidates if c.get("processed_by_trim")]
            log_reads("Filtered cutadapt/trimmomatic reads (raw available)", removed)
            candidates = raw_candidates
        oldest = select_most_ancestral(candidates)
        removed = [c for c in candidates if c not in oldest]
        log_reads("Filtered non-ancestral reads", removed)
        candidates = oldest
        seen_ids: set[str] = set()
        unique_reads: List[Dict[str, Any]] = []
        for reads in candidates:
            if reads["reads_id"] in seen_ids:
                continue
            seen_ids.add(reads["reads_id"])
            unique_reads.append(reads)
        log_reads("Selected reads", unique_reads)
        if not unique_reads:
            log_reads("No reads selected from", original_candidates)
        return unique_reads

    reads_candidates = collect_reads_upstream(genome_token)
    if reads_candidates:
        log_reads("Found upstream reads", reads_candidates)
    selected_reads = select_preferred_reads(reads_candidates)
    if selected_reads:
        return selected_reads

    if strain_token:
        downstream_candidates = collect_reads_downstream(strain_token)
        if downstream_candidates:
            log_reads("Found strain-downstream reads", downstream_candidates)
        selected_reads = select_preferred_reads(downstream_candidates)
        if selected_reads:
            return selected_reads

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
    candidates = [Path(output_dir) / "Microbe.1.0.xlsx", Path(output_dir) / "MIcrobe.1.0.xlsx"]
    candidates.extend(BIOSAMPLE_TEMPLATE_CANDIDATES)
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


def get_gtdb_genus_for_strain(
    headers: Dict[str, str],
    strain_name: Optional[str],
    column_cache: Dict[str, List[str]],
) -> Optional[str]:
    if not strain_name:
        return None
    table = "ddt_brick0000495"
    columns = get_table_columns(headers, table, column_cache)
    desired = [
        col
        for col in ["sdt_strain_name", "taxonomic_level_sys_oterm_name", "sdt_taxon_name"]
        if col in columns
    ]
    if "sdt_strain_name" not in desired or "sdt_taxon_name" not in desired:
        return None
    rows = select_all_rows(
        headers,
        table,
        columns=desired,
        filters=[{"column": "sdt_strain_name", "operator": "=", "value": strain_name}],
    )
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


def generate_biosample_table(
    genome_data: List[Dict[str, Any]], output_file: str, output_dir: str
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
        formatted_sample_name = f"environmental sample {sample_name} isolate {strain_name}".strip()
        genus = genome.get("gtdb_genus")
        organism_name = build_organism_name(genus, strain_name)

        material = (sample.get("material_name") or "").lower()
        isolation_source = None
        if "soil" in material:
            isolation_source = f"Soil sample {sample_name}".strip()
        elif "groundwater" in material:
            isolation_source = f"Groundwater sample{sample_name}".strip()

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
            "depth": sample.get("depth_meter") or "",
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
) -> None:
    fieldnames = [
        "sample_name",
        "library_ID",
        "title",
        "library_strategy",
        "library_source",
        "library_selection",
        "library_layout",
        "platform",
        "instrument_model",
        "filetype",
        "filename",
        "filename2",
    ]

    with open(output_file, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, extrasaction="ignore", delimiter="\t"
        )
        writer.writeheader()

        for genome in genome_data:
            strain = genome.get("strain", {}) or {}
            sample = genome.get("sample", {}) or {}
            sample_name = strain.get("strain_name") or genome.get("genome_name", "")
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
                    library_layout = "SINGLE"
                    primary_reads = reads_group[0] if reads_group else None
                    filename = (primary_reads.get("link") or "").split("/")[-1] if primary_reads else ""
                    filename2 = None

                if not primary_reads:
                    continue

                protocol_names = []
                protocol_names.extend(normalize_protocol_names(sample.get("protocol")))
                protocol_names.extend(primary_reads.get("protocols", []))
                platform, instrument_model = infer_platform_from_protocols(
                    protocol_names, headers, column_cache, protocol_cache
                )

                if not platform:
                    seq_tech = (primary_reads.get("sequencing_technology") or "").lower()
                    if "illumina" in seq_tech:
                        platform = "ILLUMINA"
                        instrument_model = "Illumina NovaSeq 6000"
                    elif "nanopore" in seq_tech or "ont" in seq_tech:
                        platform = "OXFORD_NANOPORE"
                        instrument_model = "PromethION"
                    elif "pacbio" in seq_tech:
                        platform = "PACBIO_SMRT"
                        instrument_model = "PacBio Sequel"
                    else:
                        platform = "ILLUMINA"
                        instrument_model = "Illumina NovaSeq 6000"

                row_data = {
                    "sample_name": sample_name,
                    "library_ID": base_name or primary_reads.get("reads_name", ""),
                    "title": f"Genome sequencing of {sample_name}",
                    "library_strategy": "WGS",
                    "library_source": "GENOMIC",
                    "library_selection": "RANDOM",
                    "library_layout": library_layout,
                    "platform": platform,
                    "instrument_model": instrument_model,
                    "filetype": "fastq",
                    "filename": filename,
                }
                if filename2:
                    row_data["filename2"] = filename2
                writer.writerow(row_data)


def generate_genome_table(
    genome_data: List[Dict[str, Any]],
    output_file: str,
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    protocol_cache: Dict[str, Dict[str, Optional[str]]],
) -> None:
    fieldnames = [
        "Biosample",
        "Organism",
        "Assembly method",
        "Sequencing technology",
        "Coverage",
        "Fasta file path",
        "Genome name",
    ]

    with open(output_file, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, extrasaction="ignore", delimiter="\t"
        )
        writer.writeheader()

        for genome in genome_data:
            strain = genome.get("strain", {}) or {}
            sample_name = strain.get("strain_name") or genome.get("genome_name", "")

            assembly_protocols = collect_protocols_from_processes(
                genome.get("assembly_processes", []) or []
            )
            assembly_method = infer_assembly_method_from_protocols(
                assembly_protocols, headers, column_cache, protocol_cache
            )

            seq_techs = infer_sequencing_techs(
                assembly_protocols, headers, column_cache, protocol_cache
            )
            if not seq_techs:
                for reads in genome.get("reads", []) or []:
                    tech = reads.get("sequencing_technology")
                    if tech:
                        seq_techs.append(tech)
            sequencing_technology = "; ".join(sorted(set(seq_techs))) if seq_techs else None

            genome_link = genome.get("genome_link") or ""
            if genome_link:
                strain_name = strain.get("strain_name") or ""
                if strain_name:
                    fasta_path = f"{genome_link.rstrip('/')}/{strain_name}_contigs.fasta"
                else:
                    fasta_path = f"{genome_link.rstrip('/')}/contigs.fasta"
            else:
                fasta_path = None

            writer.writerow(
                {
                    "Biosample": sample_name,
                    "Organism": None,
                    "Assembly method": assembly_method,
                    "Sequencing technology": sequencing_technology,
                    "Coverage": None,
                    "Fasta file path": fasta_path,
                    "Genome name": genome.get("genome_name", ""),
                }
            )


def process_genomes_for_submission(
    headers: Dict[str, str],
    genome_names: Sequence[str],
    output_dir: str = DEFAULT_OUTPUT_DIR,
    debug: bool = False,
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

    log_info("Writing biosample table")
    generate_biosample_table(
        genome_data,
        os.path.join(output_dir, "biosample_table_Microbe.1.0.xlsx"),
        output_dir,
    )
    log_info("Writing SRA metadata table")
    generate_sra_table(
        genome_data,
        os.path.join(output_dir, "sra_table.tsv"),
        headers,
        column_cache,
        protocol_cache,
    )
    log_info("Writing genome metadata table")
    generate_genome_table(
        genome_data,
        os.path.join(output_dir, "genome_table.tsv"),
        headers,
        column_cache,
        protocol_cache,
    )

    print("Generated submission tables:")
    print(f"  - {os.path.join(output_dir, 'biosample_table_Microbe.1.0.xlsx')}")
    print(f"  - {os.path.join(output_dir, 'sra_table.tsv')}")
    print(f"  - {os.path.join(output_dir, 'genome_table.tsv')}")

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
        "--debug",
        action="store_true",
        help="Enable verbose debugging, including BERDL API calls.",
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
    genome_names = load_genome_names(args)
    if not genome_names:
        raise SystemExit("No genomes provided. Use --genome-name or --genome-list.")
    headers = get_headers()
    process_genomes_for_submission(
        headers, genome_names, output_dir=args.output_dir, debug=args.debug
    )


if __name__ == "__main__":
    main()
