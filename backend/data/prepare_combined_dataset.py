"""
Extracts, converts, remaps, and resizes real training data for VisiReport AI
directly from the user's own dataset zip (archive (14).zip), which contains:

  - DeepPCB/{train,valid,test}/{images,labels}
      raw-pixel-bbox format "x1 y1 x2 y2 class_id" (1-indexed), same as the
      original DeepPCB GitHub repo. 6 classes: open, short, mousebite, spur,
      copper, pin-hole (ids 1-6 -> YOLO 0-5).

  - PKU-Market-PCB(Data enhanced version)/{train,valid,test}/{images,labels}
      already-normalized YOLO-format labels, 6 classes: missing_hole,
      mouse_bite, open_circuit, short, spur, spurious_copper (ids 0-5).
      Train images exist as a "base" capture plus 3 augmented crops
      (suffixed _1/_2/_3); valid/test splits contain only augmented crops.

VisiReport's defect taxonomy is EXTENDED from 6 to 7 classes here, because
PKU's "missing_hole" is a genuinely different defect from DeepPCB's
"pin-hole" (a missing drilled hole vs. a pit/void defect in copper) - they
are not merged into one class.

Final unified taxonomy (id: name):
  0 open        (DeepPCB "open", PKU "open_circuit")
  1 short       (DeepPCB "short", PKU "short")
  2 mousebite   (DeepPCB "mousebite", PKU "mouse_bite")
  3 spur        (DeepPCB "spur", PKU "spur")
  4 copper      (DeepPCB "copper", PKU "spurious_copper")
  5 pin-hole    (DeepPCB "pin-hole" only)
  6 missing-hole (PKU "missing_hole" only)

PKU's raw source archive ("archive (15).zip" / PCB_DATASET, XML/VOC
annotations) is intentionally NOT used - it is the pre-augmentation source
that PKU-Market-PCB(Data enhanced version) is already derived from, so it
carries no additional information beyond what's sampled here.

Because the PKU portion of the zip alone is ~10GB (high-resolution photos),
a bounded, class-balanced sample is taken and every image is resized to a
1280px-longest-side cap (bicubic, quality 88) before being written out -
YOLO normalized label coordinates are scale-invariant under uniform resize,
so this does not affect label correctness.

Usage:
    DATASET_ZIP="/path/to/archive (14).zip" OUT_DIR=combined_yolo_dataset \
        python prepare_combined_dataset.py

This is the exact script used to build backend/data/combined_yolo_dataset/
for the shipped weights - re-run it against your own copy of the zip to
regenerate (or resample with different PKU_TRAIN_PER_CLASS/PKU_VAL_PER_CLASS
values) an identical or larger dataset. Safe to interrupt and re-run: it
skips any image/label pair whose output file already exists.
"""
import os
import random
import re
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

ZIP_PATH = Path(os.environ.get("DATASET_ZIP", "archive (14).zip"))
OUT = Path(os.environ.get("OUT_DIR", "combined_yolo_dataset"))

CLASS_NAMES = ["open", "short", "mousebite", "spur", "copper", "pin-hole", "missing-hole"]

DEEPPCB_ID_TO_NEW = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
PKU_ID_TO_NEW = {0: 6, 1: 2, 2: 0, 3: 1, 4: 3, 5: 4}
PKU_CLASS_SLUGS = ["missing_hole", "mouse_bite", "open_circuit", "short", "spur", "spurious_copper"]

RESIZE_MAX_SIDE = 1280
JPEG_QUALITY = 88
PKU_TRAIN_PER_CLASS = 70
PKU_VAL_PER_CLASS = 20
SEED = 42

random.seed(SEED)


def resize_and_save_jpeg(raw_bytes: bytes, dest: Path) -> bool:
    if dest.exists():
        return False
    img = Image.open(BytesIO(raw_bytes)).convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > RESIZE_MAX_SIDE:
        scale = RESIZE_MAX_SIDE / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BICUBIC)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=JPEG_QUALITY)
    return True


def convert_deeppcb_label(raw_text: str, img_w: int, img_h: int) -> list[str]:
    lines = []
    for raw in raw_text.strip().splitlines():
        parts = raw.replace(",", " ").split()
        if len(parts) != 5:
            continue
        x1, y1, x2, y2, cls_id = (int(float(v)) for v in parts)
        new_cls = DEEPPCB_ID_TO_NEW.get(cls_id)
        if new_cls is None:
            continue
        cx = ((x1 + x2) / 2) / img_w
        cy = ((y1 + y2) / 2) / img_h
        w = abs(x2 - x1) / img_w
        h = abs(y2 - y1) / img_h
        lines.append(f"{new_cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def remap_pku_label(raw_text: str) -> list[str] | None:
    lines = []
    for raw in raw_text.strip().splitlines():
        parts = raw.split()
        if len(parts) != 5:
            continue
        old_cls = int(parts[0])
        new_cls = PKU_ID_TO_NEW.get(old_cls)
        if new_cls is None:
            return None
        lines.append(" ".join([str(new_cls)] + parts[1:]))
    return lines


def process_deeppcb(z: zipfile.ZipFile):
    print("=== DeepPCB (raw-bbox -> unified YOLO ids 0-5) ===")
    for split, out_split in (("train", "train"), ("valid", "val")):
        img_prefix = f"DeepPCB/{split}/images/"
        lbl_prefix = f"DeepPCB/{split}/labels/"
        names = [n for n in z.namelist() if n.startswith(img_prefix) and n.lower().endswith(".jpg")]
        kept = 0
        for img_name in names:
            stem = img_name[len(img_prefix):-4]
            lbl_name = f"{lbl_prefix}{stem}.txt"
            if lbl_name not in z.namelist():
                continue
            dest_img = OUT / "images" / out_split / f"deeppcb_{stem}.jpg"
            dest_lbl = OUT / "labels" / out_split / f"deeppcb_{stem}.txt"
            if dest_img.exists() and dest_lbl.exists():
                kept += 1
                continue
            img_bytes = z.read(img_name)
            img = Image.open(BytesIO(img_bytes))
            w, h = img.size
            yolo_lines = convert_deeppcb_label(z.read(lbl_name).decode(), w, h)
            if not yolo_lines:
                continue
            resize_and_save_jpeg(img_bytes, dest_img)
            dest_lbl.parent.mkdir(parents=True, exist_ok=True)
            dest_lbl.write_text("\n".join(yolo_lines) + "\n")
            kept += 1
        print(f"  {split} -> {out_split}: {kept} image/label pairs")


def process_pku(z: zipfile.ZipFile):
    print("=== PKU-Market-PCB (Data enhanced version) (remap -> unified YOLO ids) ===")
    base = "PKU-Market-PCB(Data enhanced version)"
    all_names = z.namelist()

    for split, out_split, per_class in (
        ("train", "train", PKU_TRAIN_PER_CLASS),
        ("valid", "val", PKU_VAL_PER_CLASS),
    ):
        img_prefix = f"{base}/{split}/images/"
        lbl_prefix = f"{base}/{split}/labels/"
        images = [n for n in all_names if n.startswith(img_prefix) and n.lower().endswith(".jpg")]

        by_class: dict[str, list[str]] = {slug: [] for slug in PKU_CLASS_SLUGS}
        base_only_pattern = re.compile(r"^\d+_[a-z_]+_\d+\.jpg$")
        for n in images:
            fname = n[len(img_prefix):]
            for slug in PKU_CLASS_SLUGS:
                if f"_{slug}_" in fname:
                    by_class[slug].append(fname)
                    break

        total_kept = 0
        for slug, files in by_class.items():
            if split == "train":
                candidates = [f for f in files if base_only_pattern.match(f)]
                if not candidates:
                    candidates = files
            else:
                candidates = files
            random.shuffle(candidates)
            chosen = candidates[:per_class]
            for fname in chosen:
                img_name = f"{img_prefix}{fname}"
                lbl_name = f"{lbl_prefix}{fname[:-4]}.txt"
                if lbl_name not in all_names:
                    continue
                dest_img = OUT / "images" / out_split / f"pku_{fname}"
                dest_lbl = OUT / "labels" / out_split / f"pku_{fname[:-4]}.txt"
                if dest_img.exists() and dest_lbl.exists():
                    total_kept += 1
                    continue
                remapped = remap_pku_label(z.read(lbl_name).decode())
                if not remapped:
                    continue
                img_bytes = z.read(img_name)
                resize_and_save_jpeg(img_bytes, dest_img)
                dest_lbl.parent.mkdir(parents=True, exist_ok=True)
                dest_lbl.write_text("\n".join(remapped) + "\n")
                total_kept += 1
        print(f"  {split} -> {out_split}: {total_kept} image/label pairs "
              f"({', '.join(f'{s}={len(by_class[s][:per_class]) if False else min(len(by_class[s]), per_class)}' for s in PKU_CLASS_SLUGS)})")


def main():
    OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as z:
        process_deeppcb(z)
        process_pku(z)

    data_yaml = OUT / "data.yaml"
    data_yaml.write_text(
        "path: {}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n".format(OUT.resolve())
        + "".join(f"  {i}: {name}\n" for i, name in enumerate(CLASS_NAMES))
    )
    n_train = len(list((OUT / "images" / "train").glob("*.jpg")))
    n_val = len(list((OUT / "images" / "val").glob("*.jpg")))
    print(f"\nDONE. train={n_train} val={n_val}")
    print(f"Wrote {data_yaml}")


if __name__ == "__main__":
    main()
