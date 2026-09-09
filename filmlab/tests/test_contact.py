import numpy as np
import pytest

from filmlab.contact import contact_sheet


def test_sheet_is_larger_than_a_single_frame():
    frames = [np.full((16, 24, 3), 0.5, dtype=np.float32) for _ in range(4)]
    sheet = contact_sheet(frames, [f"{i:04d}" for i in range(4)], columns=2)
    assert sheet.shape[0] > 16
    assert sheet.shape[1] > 24
    assert sheet.dtype == np.float32


def test_sheet_has_a_dark_rebate_border():
    frames = [np.ones((16, 24, 3), dtype=np.float32)]
    sheet = contact_sheet(frames, ["0001"], columns=1)
    assert sheet[0, 0, 0] < 0.2  # the border, not the frame


def test_empty_input_raises():
    with pytest.raises(ValueError, match="no frames"):
        contact_sheet([], [], columns=2)


def test_mismatched_labels_raise():
    with pytest.raises(ValueError, match="labels"):
        contact_sheet([np.zeros((4, 4, 3), dtype=np.float32)], [], columns=1)
