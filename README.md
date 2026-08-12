# VisiReport AI

Full-stack Automated Optical Inspection (AOI) console for medical-grade PCB Assembly (PCBA)
defect detection, built to ISO 13485:2016 (Cl. 8.3 & 8.5.2) traceability requirements.

Real YOLOv8 inference (fine-tuned on the public [DeepPCB](https://github.com/tangsanli5201/DeepPCB)
dataset) with real tiling/merge for up to 4K images, real JSON Schema validation, a real RabbitMQ
producer/consumer pipeline, real LLM-generated NCR narratives (Anthropic/OpenAI), real PostgreSQL
persistence, and real multi-page PDF export. See `docs/BUILD_NOTES.md` for exactly what is "real"
vs. what needs your own API key to fully light up.

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

## Re-training the model

The shipped `backend/weights/best.pt` was fine-tuned on a CPU-only sandbox with a time-boxed
subset of DeepPCB (500 train / 100 val images, 12 epochs @ 416px) - see `docs/BUILD_NOTES.md`
for the measured mAP. To retrain on the full dataset (recommended on a GPU box for real
production use):

```bash
cd backend/data
git clone https://github.com/tangsanli5201/DeepPCB.git
python prepare_dataset.py      # edit MAX_TRAIN/MAX_VAL to use the full 1500 images
yolo detect train data=yolo_dataset/data.yaml model=yolov8n.pt epochs=100 imgsz=640 device=0
python record_model_run.py     # copies best.pt + writes model_metrics.json for the System Performance tab
```

## Environment variables

See `.env.example` for the full list. The most important ones to change before any real use:

- `JWT_SECRET` - set to a long random string
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` - required for narrative generation (see `LLM_PROVIDER`)
- `SEED_ENGINEER_PASSWORD` - change from the default before exposing this beyond localhost
