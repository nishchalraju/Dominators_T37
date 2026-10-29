# External datasets - place downloaded files here

This application **never downloads** the datasets below: each has its own access conditions. Obtain them yourself,
unpack them into the matching folder, then run the inspection (`python scripts/inspect_datasets.py`, or the
"Inspect" button on the *Dataset and AI Evaluation* page when signed in as the administrator).

| Folder | Dataset | Where to get it |
|---|---|---|
| `cufs/` | CUHK Face Sketch Database (CUFS) | <https://mmlab.ie.cuhk.edu.hk/datasets.html> |
| `cufsf/` | CUHK Face Sketch FERET (CUFSF) - sketches; FERET photos come from NIST | <https://mmlab.ie.cuhk.edu.hk/archive/cufsf/> |
| `uom_sgfs/` | UoM-SGFS composite sketches (University of Malta) | <https://staff.um.edu.mt/reuben.farrugia/codedata/uom-sgfs> |

**Check the licence before use** (research-only, citation, third-party photo agreements, no redistribution). Nothing in
this folder is committed to version control (see `backend/.gitignore`). Generated or derived files belong in
`../processed/`, never here, so original data stays untouched.

Until files are really present, the web page shows **0 records** for these datasets - that is correct, not a bug.
