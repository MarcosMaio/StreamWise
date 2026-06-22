# Legacy — course reference (archived)

This directory preserves the **original UNIPDS TensorFlow.js e-commerce recommendation demo**. It is **not part of the StreamWise MVP runtime** and exists only as a historical reference for the Two-Tower / in-browser training concepts described in `docs/STREAMWISE-PLANNING.md` §17.

## Status

| Item | Notes |
|---|---|
| Runtime | Archived — do not deploy with StreamWise |
| Dependencies | Standalone `npm` project under `legacy/` |
| Replacement | StreamWise uses FastAPI + PostgreSQL + offline TensorFlow training |

## Run locally (optional)

```bash
cd legacy
npm install
npm start
```

Open `http://localhost:3000` (conflicts with StreamWise web if both run on the same port).

See also [README-legacy.md](./README-legacy.md) for the original course documentation.
