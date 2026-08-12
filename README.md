# VisiReport AI

Full-stack Automated Optical Inspection (AOI) console for medical-grade PCB Assembly (PCBA)
defect detection, built to ISO 13485:2016 (Cl. 8.3 & 8.5.2) traceability requirements.

Real YOLOv8 inference - fine-tuned on your own real datasets (DeepPCB + PKU-Market-PCB, see
"Datasets" below), a real 7-class defect taxonomy - with real tiling/merge for up to 4K images,
real JSON Schema validation, a real RabbitMQ producer/consumer pipeline, real LLM-generated NCR
narratives (Anthropic/OpenAI), real PostgreSQL persistence, and real multi-page PDF export. See
`docs/BUILD_NOTES.md` for exactly what is "real" vs. what needs your own API key to fully light up.

## Quick start

```bash
cp .env.example .env
# Edit .env: at minimum set JWT_SECRET, and set ANTHROPIC_API_KEY or OPENAI_API_KEY
# to enable live NCR narrative generation (see docs/BUILD_NOTES.md).

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API + Swagger docs: http://localhost:8000/docs
- RabbitMQ management UI: http://localhost:15672 (guest/guest)

Seed login (created automatically on first boot):

```
email:    engineer@visireport.ai
password: change-me-please   (change SEED_ENGINEER_PASSWORD in .env before real use)
```

## Repository layout

```
visireport-ai/
├── docker-compose.yml
├── backend/            FastAPI app, vision pipeline, messaging, cognitive layer, reporting
│   ├── app/
│   ├── weights/best.pt          real fine-tuned YOLOv8n weights (see docs/BUILD_NOTES.md)
│   ├── alembic/                 DB migrations
│   ├── data/                    dataset prep + training scripts (not needed to run the app)
│   └── tests/                   pytest + httpx test suite
└── frontend/           React + TypeScript + Tailwind, "Industrial Medical-Grade AOI Console" theme
    └── src/
```

## Running backend tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Datasets

The shipped weights are fine-tuned on **your own real datasets**, not a synthetic or
purely-public one:

- **DeepPCB** (`tangsanli5201/DeepPCB` on GitHub / the `liuxiaolong1/pcb-defect-detection-dataset`
  Kaggle mirror) - 6 defect classes: open, short, mousebite, spur, copper, pin-hole.
- **PKU-Market-PCB (Data enhanced version)** - a separate, real PCB defect dataset you provided
  (`archive (14).zip`), with 6 defect classes: missing_hole, mouse_bite, open_circuit, short,
  spur, spurious_copper.

Five of PKU's six classes map 1:1 onto DeepPCB's taxonomy (open_circuit&harr;open,
mouse_bite&harr;mousebite, spur&harr;spur, short&harr;short, spurious_copper&harr;copper).
PKU's sixth class, **missing_hole** (an absent drilled hole), is a genuinely different defect
from DeepPCB's **pin-hole** (a pit/void defect in copper) - so rather than merging two distinct
defect types into one label, the taxonomy was extended from 6 to **7 classes**, adding
`missing-hole`. This touches every layer: the `VISIREPORT_SCHEMA` class enum, `DEFECT_TAXONOMY`,
the annotated-image color palette, and the frontend theme tokens/Tailwind config all define all
7 classes consistently.

A third zip you provided (`archive (15).zip`, `PCB_DATASET` with XML/VOC annotations) was
**not** used for training - it's the raw, pre-augmentation source that PKU-Market-PCB (Data
enhanced version) is already derived from, so it carries no additional information beyond what
`archive (14).zip` already provides in ready-to-train YOLO format.

`backend/data/prepare_combined_dataset.py` is the exact script used to build the training set
from `archive (14).zip`: it converts DeepPCB's raw pixel-bbox labels to YOLO format, remaps
PKU's labels onto the unified 7-class taxonomy, takes a class-balanced sample of PKU (its
enhanced/augmented portion alone is ~10GB of high-resolution photos), resizes everything to a
1280px cap, and writes `backend/data/combined_yolo_dataset/`. The shipped run used 1620 train /
270 val images (1200/150 DeepPCB + 420/120 PKU, class-balanced).

Your original notebook (`visireportaimasterversion 1.ipynb`) used a differently-shaped
`VISIREPORT_SCHEMA` (nested `metadata`/`vision_results`, raw `bbox` array, no ISO severity or
status) for a quick Kaggle prototype. This rebuild keeps the **flat** schema from the build spec
(`report_id`/`board_id`/`defects[]` with `global_bbox{x,y,w,h}`/`iso_severity`/`status`) since
it's the one already wired through the Postgres data model, the full API contract, and the
31-test pytest suite - the notebook's schema was scratch validation logic for a mocked pipeline,
not a shape any other part of this system depends on.

## Re-training the model

The shipped `backend/weights/best.pt` was fine-tuned on a CPU-only sandbox on the combined
dataset above (1620 train / 270 val images, 10 epochs @ 416px) - see `docs/BUILD_NOTES.md` for
the measured mAP. To retrain (recommended on a GPU box for real production use, and/or with a
larger PKU sample):

```bash
cd backend/data
DATASET_ZIP="/path/to/archive (14).zip" OUT_DIR=combined_yolo_dataset python prepare_combined_dataset.py
yolo detect train data=combined_yolo_dataset/data.yaml model=yolov8n.pt epochs=100 imgsz=640 device=0
python record_model_run.py     # copies best.pt + writes model_metrics.json for the System Performance tab
```

(`prepare_dataset.py`, the original DeepPCB-only prep script pulling from the raw GitHub repo
layout, is still present for reference but superseded by `prepare_combined_dataset.py` above.)

## Environment variables

See `.env.example` for the full list. The most important ones to change before any real use:

- `JWT_SECRET` - set to a long random string
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` - required for narrative generation (see `LLM_PROVIDER`)
- `SEED_ENGINEER_PASSWORD` - change from the default before exposing this beyond localhost
