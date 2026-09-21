# ASCII path migration

All released files and directories use ASCII names. Research text is not
translated by this change. The original source, experimental results and proof
notes are byte-for-byte retained under new names. `provenance/path_migration.json`
maps each original path and SHA256 to its published path.

The public `tools/reproduce.py` entry point reads that map, verifies the original
bytes, and reconstructs the original layout in a new external output directory.
This preserves historical code identities and relative-path dependencies without
rewriting cryptographic contracts or numerical certificates. The temporary
workspace may contain historical Unicode paths; the published repository does not.

Do not run historical scripts directly in the renamed workspace. Pass the new
English driver/spec paths to `reproduce.py replay-spec`; it translates them to the
temporary layout. Original notes and receipts may mention old paths: consult the
mapping to find their renamed files. New README and reproduction commands use
the published English names.

The two copies of the redundant minimal-review ZIP were omitted because their
members used historical Unicode paths. Their original hashes and omission reason
are recorded in the map. Extracted source, plans and receipts are retained. The
remaining SOC3 ZIP also has English member names. Its original bytes can be
reconstructed exactly with the recorded name mapping and ZIP metadata; this
round-trip SHA256 is checked by the reproduction tool.

This is a path-only migration of the research material, plus corresponding changes
to release documentation and reproduction wrappers; it does not rerun the entire
experimental matrix or change the paper's measured numbers.
