#!/bin/bash
# Install ME:0000513-ME:0000515 (nanogram per milliliter per day,
# biomass production rate, time since sample collection) into the
# CORAL production ontology directory, verify it, and rerun the production CheckGeneric
# validator on every brick of coral_import/spring2019_batch_c2_20261019.
#
# The production files differ from the live files only by the three new term stanzas (.obo)
# and their six lines in the .txt hierarchy.
set -euo pipefail
R=/scratch/jmc/BERDL-ENIGMA-CORAL
P=$R/coral_import/ontology_update_20261019
L=/home/coral/prod/data_import/ontologies
K=$R/coral_import/spring2019_batch_c2_20261019

# Pre-install hashes (live files as of 2026-10-19, i.e. after the ME:0000506-0000512 install).
echo "5949d5c5ff35f30508873e9304755750e7caea5b034bbf486332e625dcff7aa3  $L/context_measurement_ontology.obo" | sha256sum -c -
echo "4c38b7a15bcd89eb06109e7486875c66140d13e17e2353692ee1f9a47c57dd4a  $L/context_measurement_ontology.txt" | sha256sum -c -

cp -p "$L/context_measurement_ontology.obo" "$P/baseline/context_measurement_ontology.pre-ME0000513.obo"
cp -p "$L/context_measurement_ontology.txt" "$P/baseline/context_measurement_ontology.pre-ME0000513.txt"
install -m 0644 "$P/production/context_measurement_ontology.obo" "$L/context_measurement_ontology.obo"
install -m 0644 "$P/production/context_measurement_ontology.txt" "$L/context_measurement_ontology.txt"

echo "2a254f15b1835d4a4300cb68c1037fa001251b117ccfc916772a686f1593da79  $L/context_measurement_ontology.obo" | sha256sum -c -
echo "4934eb6bcf548b9a011abab1244efd79035d5b3c3027e29e6c0389a0294f571b  $L/context_measurement_ontology.txt" | sha256sum -c -
for id in ME:0000513 ME:0000514 ME:0000515; do grep -q "^id: $id$" "$L/context_measurement_ontology.obo"; done
grep -q 'biomass production rate (float, +nanogram per milliliter per day)' "$L/context_measurement_ontology.txt"
grep -q "time since sample collection (float, time unit)" "$L/context_measurement_ontology.txt"
echo "ME:0000513-ME:0000515 installed in $L"

# Production CheckGeneric on every brick of the package.
M=/h/jmc/.m2/repository
CP=/h/jmc/src/java/classes
CP=$CP:$M/com/fasterxml/jackson/core/jackson-annotations/2.5.1/jackson-annotations-2.5.1.jar
CP=$CP:$M/com/fasterxml/jackson/core/jackson-core/2.5.1/jackson-core-2.5.1.jar
CP=$CP:$M/com/fasterxml/jackson/core/jackson-databind/2.5.1/jackson-databind-2.5.1.jar
CP=$CP:$M/com/opencsv/opencsv/4.3.2/opencsv-4.3.2.jar
CP=$CP:$M/org/apache/commons/commons-lang3/3.4/commons-lang3-3.4.jar
T=$(mktemp -d /tmp/checkgeneric-production-XXXXXX)
trap 'rm -rf "$T"' EXIT
javac -cp "$CP" -d "$T" "$R/tools/java/gov/lbl/enigma/app/CheckGenericProduction.java"
fail=0
for j in "$K"/json/*.json; do
  b=$(basename "$j")
  java -Xmx4g -cp "$T:$CP" gov.lbl.enigma.app.CheckGenericProduction "$j" > "$K/check/$b.production.check" 2>&1 || true
  if tail -1 "$K/check/$b.production.check" | grep -q 'Generic is OK!'; then echo "OK    $b"; else echo "FAIL  $b"; fail=1; fi
done
exit $fail
