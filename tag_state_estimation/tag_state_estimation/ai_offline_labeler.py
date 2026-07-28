"""Offline GUI for labeling marble presence in passive capture datasets."""

import argparse
import csv
from pathlib import Path

import cv2


WINDOW = "TAG Offline Marble Labeler"
LABEL_FIELDS = (
    "filename",
    "visible",
    "x_px",
    "y_px",
    "ball_source",
    "capture_reason",
)


def representative_rows(rows, limit):
    """Choose temporally spread examples from every diagnostic source."""
    if limit is None or limit <= 0 or len(rows) <= limit:
        return list(rows)
    groups = {}
    for row in rows:
        groups.setdefault(row.get("ball_source", "unknown"), []).append(row)
    selected = []
    remaining = limit
    ordered_groups = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    for index, (_source, group) in enumerate(ordered_groups):
        groups_left = len(ordered_groups) - index
        quota = min(len(group), max(1, remaining // groups_left))
        if quota == 1:
            indices = [len(group) // 2]
        else:
            indices = [round(i * (len(group) - 1) / (quota - 1)) for i in range(quota)]
        selected.extend(group[i] for i in indices)
        remaining -= quota
    selected.sort(key=lambda row: int(row.get("image_time_ns", "0")))
    return selected


def read_existing(path):
    """Return the latest saved label for each filename."""
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        return {row["filename"]: row for row in csv.DictReader(handle)}


class OfflineLabeler:
    """Review a bounded capture subset without requiring ROS or a camera."""

    def __init__(self, dataset, limit):
        self.dataset = dataset
        self.images_dir = dataset / "images"
        self.manifest_path = dataset / "capture_manifest.csv"
        self.labels_path = dataset / "presence_labels.csv"
        with self.manifest_path.open(newline="") as handle:
            self.rows = representative_rows(list(csv.DictReader(handle)), limit)
        if not self.rows:
            raise SystemExit(f"No rows found in {self.manifest_path}")
        self.labels = read_existing(self.labels_path)
        self.index = next(
            (i for i, row in enumerate(self.rows) if row["filename"] not in self.labels),
            len(self.rows) - 1,
        )
        self.frame = None
        cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW, self._on_mouse)

    def _write_labels(self):
        temporary = self.labels_path.with_suffix(".csv.tmp")
        with temporary.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            for row in self.rows:
                label = self.labels.get(row["filename"])
                if label is not None:
                    writer.writerow({field: label.get(field, "") for field in LABEL_FIELDS})
        temporary.replace(self.labels_path)

    def _save(self, visible, x_px="", y_px=""):
        row = self.rows[self.index]
        self.labels[row["filename"]] = {
            "filename": row["filename"],
            "visible": str(int(visible)),
            "x_px": x_px,
            "y_px": y_px,
            "ball_source": row.get("ball_source", ""),
            "capture_reason": row.get("capture_reason", ""),
        }
        self._write_labels()
        if self.index < len(self.rows) - 1:
            self.index += 1

    def _on_mouse(self, event, x, y, _flags, _data):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._save(True, float(x), float(y))

    def _load(self):
        row = self.rows[self.index]
        self.frame = cv2.imread(str(self.images_dir / row["filename"]))
        if self.frame is None:
            raise FileNotFoundError(row["filename"])
        display = self.frame.copy()
        existing = self.labels.get(row["filename"])
        state = "UNLABELED"
        if existing is not None:
            state = "VISIBLE" if existing["visible"] == "1" else "ABSENT"
        lines = (
            f"{self.index + 1}/{len(self.rows)}  labeled={len(self.labels)}  {state}",
            f"source={row.get('ball_source', '')}  reason={row.get('capture_reason', '')}",
            "V=visible  N=absent  click=visible+center  B=back  S=skip  Q=quit",
        )
        for line_index, text in enumerate(lines):
            y = 22 + 24 * line_index
            cv2.putText(display, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(display, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                        (0, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(WINDOW, display)

    def run(self):
        while True:
            self._load()
            key = cv2.waitKey(0) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("v"):
                self._save(True)
            elif key == ord("n"):
                self._save(False)
            elif key == ord("b"):
                self.index = max(0, self.index - 1)
            elif key == ord("s"):
                self.index = min(len(self.rows) - 1, self.index + 1)
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    labeler = OfflineLabeler(args.dataset.expanduser(), args.limit)
    labeler.run()
    print(f"Saved {len(labeler.labels)} labels to {labeler.labels_path}")


if __name__ == "__main__":
    main()
