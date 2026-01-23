"""
Generate NCBI SRA and Genome submission templates from BERDL provenance data.

This script walks provenance from genomes to find:
1. Raw reads with FASTQ files on genomcs.lbl.gov
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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.walk_provenance import (  # noqa: E402
    discover_tables,
    get_table_schema,
    load_process_cache,
    parse_token,
    select_all_rows,
)


FASTQ_HOST = "genomcs.lbl.gov"
DEFAULT_OUTPUT_DIR = "ncbi_submission"
PROTOCOL_TABLE = "sdt_protocol"


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
    headers: Dict[str, str],
    column_cache: Dict[str, List[str]],
    read_cache: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    visited: set[str] = set()
    reads_candidates: List[Dict[str, Any]] = []

    def walk_upstream(obj_token: str, depth: int = 0, path: Optional[List[str]] = None) -> None:
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
            if obj_id in read_cache:
                reads_data = read_cache[obj_id]
            else:
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

            link = reads_data.get("link")
            if link and FASTQ_HOST in link.lower():
                if ".fastq" in link.lower() or ".fq" in link.lower():
                    protocols = []
                    for proc in out_lookup.get(obj_token, []):
                        protocols.extend(normalize_protocol_names(proc.get("protocol")))
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

    walk_upstream(genome_token)

    oldest_reads: List[Dict[str, Any]] = []
    for reads in reads_candidates:
        reads_id = reads["reads_id"]
        path = reads["path"]
        is_oldest = True
        for other_reads in reads_candidates:
            if other_reads["reads_id"] == reads_id:
                continue
            for path_token in path:
                other_table, other_obj_id = parse_token(path_token)
                if other_table == "sdt_reads" and other_obj_id == other_reads["reads_id"]:
                    is_oldest = False
                    break
            if not is_oldest:
                break
        if is_oldest:
            oldest_reads.append(reads)

    seen_ids: set[str] = set()
    unique_reads = []
    for reads in oldest_reads:
        if reads["reads_id"] in seen_ids:
            continue
        seen_ids.add(reads["reads_id"])
        unique_reads.append(reads)

    return unique_reads


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


def generate_biosample_table(genome_data: List[Dict[str, Any]], output_file: str) -> None:
    fieldnames = [
        "sample_name",
        "organism",
        "collection_date",
        "geo_loc_name",
        "isolation_source",
        "lat_lon",
        "host",
        "host_disease",
        "isolation_source",
        "env_biome",
        "env_feature",
        "env_material",
        "depth",
        "altitude",
        "description",
    ]

    with open(output_file, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for genome in genome_data:
            sample = genome.get("sample", {}) or {}
            location = genome.get("location", {}) or {}
            strain = genome.get("strain", {}) or {}

            lat_lon = None
            if location.get("latitude") is not None and location.get("longitude") is not None:
                lat_lon = f"{location['latitude']} {location['longitude']}"

            geo_loc_name_parts = []
            if location.get("country"):
                geo_loc_name_parts.append(location["country"])
            if location.get("region"):
                geo_loc_name_parts.append(location["region"])
            geo_loc_name = ": ".join(geo_loc_name_parts) if geo_loc_name_parts else None

            sample_name = (
                strain.get("strain_name")
                or sample.get("sample_name")
                or genome.get("genome_name", "")
            )

            writer.writerow(
                {
                    "sample_name": sample_name,
                    "organism": None,
                    "collection_date": sample.get("date"),
                    "geo_loc_name": geo_loc_name,
                    "isolation_source": sample.get("material_name"),
                    "lat_lon": lat_lon,
                    "env_biome": location.get("biome"),
                    "depth": sample.get("depth_meter"),
                    "description": strain.get("description") or sample.get("description"),
                }
            )


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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
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
) -> List[Dict[str, Any]]:
    os.makedirs(output_dir, exist_ok=True)
    column_cache: Dict[str, List[str]] = {}
    protocol_cache: Dict[str, Dict[str, Optional[str]]] = {}
    read_cache: Dict[str, Dict[str, Any]] = {}

    discovered_tables = discover_tables(headers)
    cache = load_process_cache(headers, discovered_tables)

    genome_columns = get_table_columns(headers, "sdt_genome", column_cache)
    genome_desired = [
        col
        for col in ["sdt_genome_id", "sdt_genome_name", "sdt_strain_name", "link"]
        if col in genome_columns
    ]

    genome_data: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for genome_name in genome_names:
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

        reads_list = find_oldest_reads_with_fastq(
            genome_token, cache.out_lookup, headers, column_cache, read_cache
        )
        if not reads_list:
            warnings.append(
                f"Genome {genome_name}: No reads with FASTQ files on {FASTQ_HOST} found"
            )

        samples_list = find_samples_from_genome(
            genome_token, cache.out_lookup, headers, column_cache
        )
        sample_data = samples_list[0] if samples_list else None
        location_data = None
        if sample_data and sample_data.get("location_name"):
            location_data = get_location_info(
                headers, sample_data["location_name"], column_cache
            )

        strain_data = get_strain_info(headers, strain_name, column_cache) if strain_name else None

        assembly_processes = find_assembly_processes(genome_token, cache.out_lookup)

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
            }
        )

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    generate_biosample_table(genome_data, os.path.join(output_dir, "biosample_table.csv"))
    generate_sra_table(
        genome_data,
        os.path.join(output_dir, "sra_table.csv"),
        headers,
        column_cache,
        protocol_cache,
    )
    generate_genome_table(
        genome_data,
        os.path.join(output_dir, "genome_table.csv"),
        headers,
        column_cache,
        protocol_cache,
    )

    print("Generated submission tables:")
    print(f"  - {os.path.join(output_dir, 'biosample_table.csv')}")
    print(f"  - {os.path.join(output_dir, 'sra_table.csv')}")
    print(f"  - {os.path.join(output_dir, 'genome_table.csv')}")

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
    process_genomes_for_submission(headers, genome_names, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
