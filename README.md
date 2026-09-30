# docs-tools

Tools for the `~/text/docs` subtitle and SUPER document workflow.

Build a Markdown reference from the latest four completed `doc-N` folders:

```bash
python3 ref_docs.py
```

The generator selects folders containing one source TXT with `chus`, one with
`super`, and both corresponding final DOCX files under `output/`. It writes
`~/text/docs/refs/latest-4-docs.md` by default.

Use `--latest N` to change the number of folders, `--root` to use another
document root, or `--dry-run`/`--check` to avoid rewriting the reference.
