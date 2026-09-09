"""Contact sheet rendering, in the style of a 35 mm proof print."""

from __future__ import annotations

import cv2
import numpy as np

_BORDER_FRAC = 0.06
_LABEL_HEIGHT_FRAC = 0.12
_REBATE = 0.08  # near-black, like unexposed film base
_INK = np.array([0.85, 0.78, 0.55], dtype=np.float32)  # warm frame-number ink


def contact_sheet(
    images: list[np.ndarray], labels: list[str], columns: int = 4
) -> np.ndarray:
    """Tile developed frames onto a dark rebate with frame numbers beneath each."""
    if not images:
        raise ValueError("no frames to lay out")
    if len(labels) != len(images):
        raise ValueError("labels must match the number of frames")

    height, width = images[0].shape[:2]
    border = max(int(round(width * _BORDER_FRAC)), 4)
    label_h = max(int(round(height * _LABEL_HEIGHT_FRAC)), 12)
    cell_w = width + border * 2
    cell_h = height + border * 2 + label_h

    columns = max(1, min(columns, len(images)))
    rows = (len(images) + columns - 1) // columns
    sheet = np.full((rows * cell_h, columns * cell_w, 3), _REBATE, dtype=np.float32)

    # cv2.putText requires an 8-bit image (CV_8U), so frame numbers are drawn into
    # a single-channel uint8 layer and composited into the float sheet afterwards.
    # Compositing rather than converting the sheet keeps the frames at full float
    # precision and preserves the text's antialiasing.
    ink_layer = np.zeros(sheet.shape[:2], dtype=np.uint8)

    for i, (frame, label) in enumerate(zip(images, labels)):
        resized = frame
        if frame.shape[:2] != (height, width):
            resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        r, c = divmod(i, columns)
        y = r * cell_h + border
        x = c * cell_w + border
        sheet[y : y + height, x : x + width] = np.clip(resized, 0.0, 1.0)
        cv2.putText(
            ink_layer,
            label,
            (x, y + height + int(label_h * 0.75)),
            cv2.FONT_HERSHEY_SIMPLEX,
            max(height / 900.0, 0.3),
            255,
            1,
            cv2.LINE_AA,
        )

    mask = (ink_layer.astype(np.float32) / 255.0)[..., None]
    sheet = sheet * (1.0 - mask) + _INK * mask
    return np.clip(sheet, 0.0, 1.0).astype(np.float32)
