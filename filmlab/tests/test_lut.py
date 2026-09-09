import numpy as np
import pytest

from filmlab.lut import apply_lut, load_cube

_IDENTITY_CUBE = """TITLE "identity"
LUT_3D_SIZE 2
0.0 0.0 0.0
1.0 0.0 0.0
0.0 1.0 0.0
1.0 1.0 0.0
0.0 0.0 1.0
1.0 0.0 1.0
0.0 1.0 1.0
1.0 1.0 1.0
"""


def test_load_cube_shape(tmp_path):
    p = tmp_path / "id.cube"
    p.write_text(_IDENTITY_CUBE)
    lut = load_cube(p)
    assert lut.shape == (2, 2, 2, 3)
    assert lut.dtype == np.float32


def test_load_cube_rejects_a_file_without_a_size(tmp_path):
    p = tmp_path / "bad.cube"
    p.write_text("0.0 0.0 0.0\n")
    with pytest.raises(ValueError, match="LUT_3D_SIZE"):
        load_cube(p)


def test_identity_lut_is_close_to_a_no_op(tmp_path):
    p = tmp_path / "id.cube"
    p.write_text(_IDENTITY_CUBE)
    lut = load_cube(p)
    img = np.random.default_rng(0).random((8, 8, 3)).astype(np.float32)
    assert np.allclose(apply_lut(img, lut), img, atol=1e-5)
