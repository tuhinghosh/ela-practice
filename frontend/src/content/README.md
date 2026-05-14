# Frontend content mirror

The JSON files in this directory are a **generated mirror** of the
canonical content under `backend/content/`. The Next.js bundler imports
them at compile time via `@/content/*`.

**Do not edit these files directly.** Edit the canonical copy under
`backend/content/`, then run:

```bash
scripts/sync-content.sh
```

That wrapper runs `python3 -m backend.app.content_cli validate` (which
also verifies `MANIFEST.json` checksums) and then copies the files here.
The test `backend/tests/test_content_workflow.py::test_frontend_mirror_matches_backend_canonical`
will fail if these files drift out of sync.
