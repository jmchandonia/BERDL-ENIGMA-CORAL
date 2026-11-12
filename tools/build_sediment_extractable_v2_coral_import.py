#!/usr/bin/env python3
"""Build hazen_sediment_extractable_fwb306_2015_v2, the replacement of Brick0002179.

Brick0002179 (sample x replicate x analyte, one variable) is complete in CORAL, but CORAL's CSV export omits blank cells
and the Lakehouse converter does not restore a blank analyte-replicate pair (it reads it as a replicate that was not
run), so the never-detected analytes and some below-limit cells had no row in enigma.coral. Version 2 adds a
"below detection limit" true/false variable, so every cell carries a value and the table keeps all 320 rows.

The measurements are unchanged: this script starts from the JSON of the loaded brick.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import comment, oterm_value, write_process  # noqa: E402

SRC = REPO / "coral_import/evo_memory_brick7_20261111/json/hazen_sediment_extractable_fwb306_2015.json"
OUT = REPO / "coral_import/sediment_extractable_v2_20261112"
OLD = "hazen_sediment_extractable_fwb306_2015.ndarray"
NEW = "hazen_sediment_extractable_fwb306_2015_v2"
TODAY = "2026-11-12"


def main():
    oo.stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(OUT)
    ab.OUT = OUT
    ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT = (OUT / d for d in ("json", "process", "check"))
    for d in (ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT):
        d.mkdir(parents=True)
    old = json.loads(SRC.read_text())
    if old["name"] != OLD or [d["size"] for d in old["dim_context"]] != [8, 2, 20] or len(old["typed_values"]) != 1:
        raise ValueError("unexpected source brick")
    conc = old["typed_values"][0]["values"]["float_values"]
    if len(conc) != 320 or sum(v is None for v in conc) != 113:
        raise ValueError("unexpected concentration values")
    below = [v is None for v in conc]
    marker = {"value_type": ab.term("data variables type"), "value": oterm_value("chemical measurement")}
    context = []
    for c in old["array_context"]:
        text = c["value"].get("string_value", "")
        if text.startswith("A blank concentration is a value the laboratory reported as below its detection limit"):
            text = text.replace("A blank concentration is a value the laboratory reported as below its detection limit; every sample was measured for every analyte.",
                                "Every sample was measured for every analyte. Where the laboratory reported a value as below its detection limit, the concentration is "
                                "blank and the below variable is true.")
            c = comment(text)
        if text.startswith("Below the detection limit in every sample (all concentrations blank)"):
            c = comment(text.replace("(all concentrations blank)", "(below is true in all 16 measurements)"))
        context.append(c)
    context.insert(1, comment(f"Replaces {OLD} (Brick0002179): the same measurements, with the below variable added so that every sample, replicate and analyte keeps a row "
                              "in the Lakehouse table"))
    obj = {"name": f"{NEW}.hndarray", "description": old["description"], "data_type": old["data_type"], "array_context": [marker] + context,
           "n_dimensions": 3, "dim_context": old["dim_context"],
           "typed_values": [old["typed_values"][0], ab.bool_var("below", ab.below_ctx(), below)]}
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / "process_update_data_sediment_extractable_v2_20261112.tsv", [{
        "process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>", "campaign": "Natural Organic Matter <ENIGMA:0000027>",
        "protocol": "null", "date_start": TODAY, "date_end": TODAY, "input_objects": f"Generic: {OLD}", "output_objects": f"Generic: {NEW}.hndarray"}])
    (OUT / "files_to_import.txt").write_text(f"json/{NEW}.json\nprocess/process_update_data_sediment_extractable_v2_20261112.tsv\n")
    (OUT / "import_to_coral.py").write_text(f"toolx.upload_brick('{NEW}.json')\ntoolx.upload_process('Update Data', 'process_update_data_sediment_extractable_v2_20261112.tsv')\n")
    print(f"below-limit cells: {sum(below)} of {len(below)}")


if __name__ == "__main__":
    main()
