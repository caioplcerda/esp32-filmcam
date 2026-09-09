import numpy as np
import pytest
import tifffile
from PIL import Image

from filmlab.io_jpeg import Metadata, read_image, read_sidecar, write_jpeg, write_tiff


def _write_test_jpeg(path):
    Image.fromarray(np.full((16, 24, 3), 128, dtype=np.uint8)).save(path, quality=95)


def test_read_image_shape_range_and_dtype(tmp_path):
    p = tmp_path / "f.jpg"
    _write_test_jpeg(p)
    img = read_image(p)
    assert img.shape == (16, 24, 3)
    assert img.dtype == np.float32
    assert 0.0 <= img.min() and img.max() <= 1.0


def test_read_image_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_image(tmp_path / "nope.jpg")


def test_read_image_rejects_empty_file(tmp_path):
    p = tmp_path / "empty.jpg"
    p.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        read_image(p)


def test_read_sidecar_parses_all_fields(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text(
        "frame=7\nmillis=812\nexposure=204\ngain=12\n"
        "awb_r=1\nawb_b=1\nframesize=UXGA\nquality=4\n"
    )
    meta = read_sidecar(p)
    assert meta.frame == 7
    assert meta.gain == 12
    assert meta.framesize == "UXGA"
    assert meta.quality == 4


def test_read_sidecar_missing_file_returns_default(tmp_path):
    meta = read_sidecar(tmp_path / "absent.txt")
    assert meta == Metadata.default()
    assert meta.gain == 0


def test_read_sidecar_ignores_malformed_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("frame=3\ngarbage\ngain=notanumber\nquality=4\n")
    meta = read_sidecar(p)
    assert meta.frame == 3
    assert meta.quality == 4
    assert meta.gain == 0  # unparseable value falls back to the default


def test_read_sidecar_empty_value_falls_back_to_default(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("frame=3\nframesize=\nquality=4\n")
    meta = read_sidecar(p)
    assert meta.framesize == "UNKNOWN"
    assert meta.frame == 3
    assert meta.quality == 4


def test_write_tiff_is_16_bit(tmp_path):
    p = tmp_path / "out.tif"
    write_tiff(p, np.full((4, 4, 3), 0.5, dtype=np.float32))
    data = tifffile.imread(p)
    assert data.dtype == np.uint16
    assert data.shape == (4, 4, 3)


def test_write_jpeg_round_trips_roughly(tmp_path):
    p = tmp_path / "out.jpg"
    write_jpeg(p, np.full((8, 8, 3), 0.25, dtype=np.float32))
    back = read_image(p)
    assert np.allclose(back, 0.25, atol=0.02)
