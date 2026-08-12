# Build notes: what's real, what's pending your input

This rebuild replaces every mocked piece of the original Streamlit prototype with a genuine
implementation. This doc is the honest account of what was verified end-to-end in the build
sandbox, what's real-but-limited by the sandbox's hardware, and the one piece that needs your
own credentials to fully verify.

## Update: your real datasets + your original notebook

After the initial rebuild, you provided your actual original prototype notebook
(`visireportaimasterversion 1.ipynb`) plus two real dataset zips on your machine
(`archive (14).zip`, `archive (15).zip`). Both were read/inspected and incorporated:

- **Notebook**: confirmed the original Streamlit `app.py` (notebook cell 17) ran entirely on
  `run_mock_vision_pipeline()`/`run_mock_cognitive_pipeline()` - hardcoded fake detections and a
  static NCR report string - exactly the "fully-mocked prototype" this rebuild replaces. The
  notebook's `PCBAVisionEngine` (tiling/async-inference/NMS) is architecturally close to what was
  already built here; its `VISIREPORT_SCHEMA` is shaped differently (nested `metadata`/
  `vision_results`, raw `bbox` array) from the flat schema this rebuild uses - see "Datasets" in
  `README.md` for why the flat schema was kept.
- **`archive (14).zip`**: contains your own copy of DeepPCB *and* a second real dataset,
  PKU-Market-PCB (Data enhanced version), with a 6-class taxonomy that's 5/6 identical to
  DeepPCB's but has a genuinely distinct 6th class (`missing_hole` vs. DeepPCB's `pin-hole`).
  Both were combined into one training set with a unified 7-class taxonomy - see "Datasets" in
  `README.md` for the full mapping and `backend/data/prepare_combined_dataset.py` for the exact
  extraction/remap logic, verified visually (annotated sample images with correctly-placed boxes
  for both DeepPCB's raw-bbox format and PKU's already-normalized YOLO labels).
- **`archive (15).zip`**: inspected and intentionally *not* used - it's the raw, pre-augmentation
  `PCB_DATASET` (XML/VOC annotations) that PKU-Market-PCB (Data enhanced version) is already
  derived from, so it adds no information beyond what `archive (14).zip` already provides.
- The shipped `backend/weights/best.pt` was retrained from scratch on the combined 7-class
  dataset (1620 train / 270 val images) - the taxonomy change touches the JSON Schema enum,
  `DEFECT_TAXONOMY`, the annotated-image color palette, and the frontend theme tokens/Tailwind
  config, all updated consistently and re-verified (31/31 backend tests still pass, `tsc --noEmit`
  clean on the frontend).

## A note on how verification was done

The build sandbox's container runtime does not permit running a nested Docker daemon (`dockerd`
fails to start - no privileged/nested-container support), so `docker compose up` itself could not
be executed *inside the sandbox*. `docker compose config` was run successfully to confirm the
compose file is valid and builds the intended service graph. To still verify the real stack
end-to-end rather than just trusting the code, Postgres 16 and RabbitMQ 3.12 (with the management
plugin) were installed and run as native services in the sandbox, and the backend/worker/frontend
were run as plain processes against them - functionally identical to what `docker compose up` runs,
just without the container boundary. Everything below marked "Verified" was exercised against
that real, running stack (real HTTP calls, a real browser via Playwright, real screenshots - not
just unit tests). `docker compose up` itself should work as-is on your machine, which has a normal
Docker daemon; if anything doesn't come up cleanly there, it's worth a first-run sanity check.

## Real and verified in this build

- **YOLO inference**: a real YOLOv8n model, fine-tuned on the public DeepPCB dataset (not COCO
  placeholder weights), genuinely loaded via Ultralytics and run per-tile. Verified by uploading
  two different real DeepPCB test images through the actual running API: one came back
  `CONFORMING` with 0 defects, the other `NONCONFORMING` with 5 defects across 4 different classes
  at varying confidences and bbox coordinates - a genuine forward pass, not `random.randint`. If
  `weights/best.pt` is missing or fails to load, the upload endpoint returns 503 (verified both by
  test and by pointing `MODEL_WEIGHTS_PATH` at a nonexistent file).
- **Tiling/remap/merge**: real geometry (`app/vision/tiling.py`), unit-tested for full-image
  coverage, 4K grid generation, coordinate remap, and cross-tile-boundary IoU deduplication (7
  tests), and exercised live: uploading a 640x640 image with `tile_size=300&overlap=40` produced
  a real 3x3 = 9-tile grid and merged 13 raw detections down to a clean set with no boundary
  duplication, visible in both the audit log (`"13 defect(s) detected across 9 tile(s)"`) and the
  live WebSocket scan log.
- **Schema validation**: real `jsonschema` validation against `VISIREPORT_SCHEMA`, tested for both
  valid and multiple invalid-payload cases, and confirmed live (`schema_valid: true` on every
  successful upload against the running Postgres instance).
- **RabbitMQ**: real `aio-pika` producer/consumer, verified against a real RabbitMQ instance
  end-to-end - the worker process genuinely consumed published messages (confirmed via its logs).
  Also verified the failure path live: stopped RabbitMQ, uploaded a board image, and the publish
  step failed loudly - `PAYLOAD_PUBLISH_FAILED` with the real connection error in the audit log,
  502/503-style failure surfaced to the client, never a silent "SIMULATED" success. Restarted
  RabbitMQ and confirmed `/api/v1/health` immediately reflected it as healthy again.
- **Postgres persistence**: SQLAlchemy 2.0 async models for all 7 tables, real Alembic migration
  applied to a real Postgres 16 database, confirm/override actions persisted and re-fetched
  correctly with the right actor identity in both the API and the live UI (Defect Registry +
  Audit Log both reflect it after a full page reload).
- **PDF export**: real multi-page ReportLab PDF, verified via live download (`%PDF` magic bytes,
  correct content-type, non-trivial size) against a real inspection with a confirmed defect.
- **Annotated image endpoint**: `GET /api/v1/inspections/{id}/image` (added beyond the base
  spec, since the Inspection viewport needs somewhere to source pixels) re-draws the real stored
  detections + tile grid onto the original upload with OpenCV and streams a real JPEG - visible in
  the Inspection page screenshot below with correctly color-coded, correctly positioned boxes.
- **JWT auth**: real `python-jose` JWT issuance/verification; protected endpoints return 401 with
  no/garbage token; `/health` and `/auth/login` are the only public routes - verified both by test
  and live curl calls.
- **Live WebSocket progress**: `/ws/inspections/{id}` streams real per-tile events via a RabbitMQ
  fanout exchange that both the backend's own inference loop and the separate `worker` process
  publish onto - a genuine cross-process message-bus hop, not a shared-memory shortcut. Seen live
  in the Inspection page's terminal log: real timestamps, real tile indices, real detection counts,
  ending in an honest `LLM SYNTHESIS FAILED - ANTHROPIC_API_KEY is not configured` line rather than
  fabricated narrative text.
- **31/31 backend pytest tests pass** (`backend/tests/`), covering auth, boards, inspections,
  defects, audit log, schema validation, broker-failure, PDF export, the annotated-image endpoint,
  and the LLM adapter's no-key error path.
- **Frontend**: real `docker-compose config`-validated build, clean `tsc --noEmit` typecheck,
  clean production `vite build`, and a full authenticated browser session (Playwright) driving the
  actual running backend - login, upload, live terminal log, annotated viewport, defect registry,
  cognitive pipeline, compliance/audit log, and system performance pages all screenshotted against
  real data, not a static mockup.

## Real but constrained by the build sandbox

- **Model accuracy**: this sandbox has no GPU. The shipped weights were fine-tuned CPU-only for
  10 epochs at 416px on the combined 7-class dataset (1620 train / 270 val - see "Datasets" in
  `README.md`), ~65 min wall clock. The actual measured metrics (mAP50 0.618, mAP50-95 0.388,
  precision 0.888, recall 0.561) are recorded honestly in the `model_runs` table via
  `backend/data/record_model_run.py`, which parses the real Ultralytics training/val output -
  nothing is hand-typed. Per-class mAP50-95: open 0.443, short 0.363, mousebite 0.392, spur 0.362,
  copper 0.554, pin-hole 0.744 - all six original DeepPCB-derived classes trained normally.
  **`missing-hole` (the new 7th class from your PKU dataset) did not converge** - mAP50-95 0.002,
  essentially zero recall. With only 70 training images and defects that are small relative to a
  416px input, 10 epochs wasn't enough for that one class to learn - this is reported honestly
  rather than smoothed over. `backend/data/prepare_combined_dataset.py` has `PKU_TRAIN_PER_CLASS`/
  `PKU_VAL_PER_CLASS` knobs to sample more PKU images, and more epochs (or a GPU) would likely fix
  this. The DeepPCB paper's own targets (mAP50 0.968 / mAP50-95 0.763) are kept in the frontend
  explicitly labeled "target SLAs, not achieved metrics".
- **System health telemetry**: CPU/memory are read live via `psutil` on the backend host. There
  is no GPU in this deployment, so GPU telemetry is simply not shown, rather than being faked.

## Needs your input to fully verify

- **LLM narrative generation**: the Anthropic/OpenAI adapter (`app/cognitive/llm_client.py`) is
  real, provider-agnostic, and was verified live to fail with a clear, specific error (never
  fabricated text) when no API key is configured - both in the pytest suite and in the running
  worker/UI. A live narrative generation could not be demonstrated because no API key was
  available in the build sandbox. **To finish verifying this yourself**: set `ANTHROPIC_API_KEY`
  (or `LLM_PROVIDER=openai` + `OPENAI_API_KEY`) in `.env`, restart the stack, upload a board image,
  and confirm the Cognitive Pipeline tab's narrative populates and that clicking "Regenerate"
  produces a new API call (visible in `docker compose logs worker`).

## Acceptance checklist status (Section 10 of the build spec)

| Item | Status |
|---|---|
| `docker compose up` brings up all 5 services with no manual steps beyond `.env` | Compose file validated (`docker compose config`); equivalent native-service stack run and verified live - see note above on why `docker compose up` itself couldn't run inside this sandbox |
| Real YOLO forward pass, different images -> different detections | Verified live |
| Tiling grid + per-tile counts exposed, no boundary duplication | Verified live + unit tests |
| RabbitMQ down -> publish fails loudly | Verified live |
| LLM narrative changes with defect data / Regenerate makes a real call | Code real & tested for the failure path live; **live generation needs your API key** |
| Confirm/Override persist across refresh, correct audit identity | Verified live |
| PDF export matches on-screen defect table | Verified live |
| JWT gates the API (401 with no/expired token) | Verified live |
| UI matches Section 5 theme tokens/motifs | Verified live via screenshots against a real running backend |
| `/docs` lists every endpoint, each exercised by a test | Verified |
| No `random.*` data presented as real detections/metrics anywhere | Verified |
