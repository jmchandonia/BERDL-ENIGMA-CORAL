/* global ARGUMENTS, print */
"use strict";
// Change the protocol of the Zhou Lab pump-test and sediment Classify OTUs processes from
// ning-lui-2021-qiime2 (QIIME2 sklearn classifier, Silva 138, confidence 0.7) to the protocols
// that describe what the lab actually ran (DADA2 RDP classifier, SILVA v138.1; see each ReadMe).
// Only the `protocol` attribute of the listed SYS_Process documents changes; their input and
// output edges are untouched.
//
//   arangosh <connection-options> --javascript.execute patch_classify_otus_protocols.js            (dry run)
//   arangosh <connection-options> --javascript.execute patch_classify_otus_protocols.js -- --apply

const fs = require("fs");
const db = require("@arangodb").db;

const COLLECTION = "SYS_Process";
const PROTOCOL_COLLECTION = "SDT_Protocol";
const patches = __PATCHES__;

const args = typeof ARGUMENTS === "undefined" ? [] : ARGUMENTS;
const apply = args.indexOf("--apply") !== -1;

function fail(message) {
  throw new Error(message);
}

function current() {
  return db
    ._query(
      `FOR p IN @patches
         LET doc = DOCUMENT(CONCAT(@collection, "/", p.id))
         RETURN { id: p.id, exists: doc != null,
                  protocol: doc == null ? null : (HAS(doc, "protocol") ? doc.protocol : null),
                  from: p.from, to: p.to }`,
      { patches: patches, collection: COLLECTION }
    )
    .toArray();
}

const targets = Object.keys(patches.reduce((acc, p) => { acc[p.to] = true; return acc; }, {}));
const found = db
  ._query(`FOR x IN @@c FILTER x.name IN @names RETURN x.name`, { "@c": PROTOCOL_COLLECTION, names: targets })
  .toArray();
const absent = targets.filter((t) => found.indexOf(t) === -1);
if (absent.length) {
  fail("Load the new protocols first; absent from SDT_Protocol: " + JSON.stringify(absent));
}

const before = current();
const missing = before.filter((r) => !r.exists).map((r) => r.id);
const pending = before.filter((r) => r.exists && r.protocol === r.from);
const done = before.filter((r) => r.exists && r.protocol === r.to);
const other = before.filter((r) => r.exists && r.protocol !== r.from && r.protocol !== r.to);
print("processes listed: " + patches.length);
print("still " + JSON.stringify(patches[0].from) + ": " + pending.length + "; already patched: " + done.length);
if (missing.length || other.length) {
  fail("Unexpected state; missing: " + JSON.stringify(missing) + "; other protocol: " + JSON.stringify(other.slice(0, 5)));
}

if (!apply) {
  print("Dry run only. Re-run with --apply to update " + pending.length + " processes.");
} else {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = "classify_otus_protocol_patch_backup_" + stamp + ".json";
  fs.write(backup, JSON.stringify({ created_at: new Date().toISOString(), before: pending }, null, 2));
  print("before-state backup: " + backup);
  const updated = db
    ._query(
      `FOR p IN @pending
         LET doc = DOCUMENT(CONCAT(@collection, "/", p.id))
         FILTER doc != null AND doc.protocol == p.from
         UPDATE doc WITH { protocol: p.to } IN @@c
         RETURN NEW._key`,
      { pending: pending, collection: COLLECTION, "@c": COLLECTION }
    )
    .toArray();
  if (updated.length !== pending.length) {
    fail("Updated " + updated.length + " of " + pending.length);
  }
  const after = current();
  const wrong = after.filter((r) => r.protocol !== r.to);
  if (wrong.length) {
    fail("Post-update check failed: " + JSON.stringify(wrong.slice(0, 5)));
  }
  print("updated " + updated.length + "; all " + after.length + " listed processes now cite their new protocol");
}
