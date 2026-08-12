"""
Convert the DeepPCB dataset (x1 y1 x2 y2 type per line, 1-indexed class ids)
into a YOLO-format dataset for the VisiReport AI defect taxonomy:

    DeepPCB id -> class key -> YOLO id
    1 open       -> 0
    2 short      -> 1
    3 mousebite  -> 2
    4 spur       -> 3
    5 copper     -> 4
    6 pin-hole   -> 5

Only the "*_test.jpg" (defective) images carry real defects; the "*_temp.jpg"
template images are defect-free references and are skipped for training.

Output layout:
    backend/data/yolo_dataset/
        images/train/*.jpg
        images/val/*.jpg
        labels/train/*.txt
        labels/val/*.txt
        data.yaml
"""
import random
import shutil
from pathlib import Path

import cv2

SRC = Path(__file__).parent / "DeepPCB" / "PCBData"
OUT = Path(__file__).parent / "yolo_dataset"

CLASS_NAMES = ["open", "short", "mousebite", "spur", "copper", "pin-hole"]
DEEPPCB_ID_TO_YOLO = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}

# Time-boxed for CPU-only training: cap the number of images used.
MAX_TRAIN = 500
MAX_VAL = 100
SEED = 42


def find_pairs():
    """Return list of (image_path, label_path) for every *_test.jpg."""
    pairs = []
    for group_dir in sorted(SRC.glob("group*")):
        img_dirs = [d for d in group_dir.iterdir() if d.is_dir() and not d.name.endswith("_not")]
        for img_dir in img_dirs:
            label_dir = group_dir / f"{img_dir.name}_not"
            if not label_dir.exists():
                continue
            for img_path in sorted(img_dir.glob("*_test.jpg")):
                stem = img_path.name.replace("_test.jpg", "")
                label_path = label_dir / f"{stem}.txt"
                if label_path.exists():
                    pairs.append((img_path, label_path))
    return pairs


def convert_label(label_path: Path, img_w: int, img_h: int) -> list[str]:
    lines = []
    for raw in label_path.read_text().strip().splitlines():
        raw = raw.replace(",", " ").split()
        if len(raw) != 5:
            continue
        x1, y1, x2, y2, cls_id = (int(float(v)) for v in raw)
        yolo_cls = DEEPPCB_ID_TO_YOLO.get(cls_id)
        if yolo_cls is None:
            continue
        cx = ((x1 + x2) / 2) / img_w
        cy = ((y1 + y2) / 2) / img_h
        w = abs(x2 - x1) / img_w
        h = abs(y2 - y1) / img_h
        lines.append(f"{yolo_cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def main():
    random.seed(SEED)
    pairs = find_pairs()
    print(f"Found {len(pairs)} annotated defect images total.")
    random.shuffle(pairs)

    n_train = min(MAX_TRAIN, int(len(pairs) * 0.85))
    n_val = min(MAX_VAL, len(pairs) - n_train)
    train_pairs = pairs[:n_train]
    val_pairs = pairs[n_train:n_train + n_val]
    print(f"Using {len(train_pairs)} train / {len(val_pairs)} val images.")

    for split, split_pairs in (("train", train_pairs), ("val", val_pairs)):
        img_out = OUT / "images" / split
        lbl_out = OUT / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        kept = 0
        for img_path, label_path in split_pairs:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            h, w = img.shape[:2]
            yolo_lines = convert_label(label_path, w, h)
            if not yolo_lines:
                continue
            dest_name = f"{img_path.parent.parent.name}_{img_path.stem}"
            shutil.copy(img_path, img_out / f"{dest_name}.jpg")
            (lbl_out / f"{dest_name}.txt").write_text("\n".join(yolo_lines) + "\n")
            kept += 1
        print(f"{split}: wrote {kept} image/label pairs")

    data_yaml = OUT / "data.yaml"
    data_yaml.write_text(
        "path: {}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n".format(OUT.resolve())
        + "".join(f"  {i}: {name}\n" for i, name in enumerate(CLASS_NAMES))
    )
    print(f"Wrote {data_yaml}")


if __name__ == "__main__":
    main()
