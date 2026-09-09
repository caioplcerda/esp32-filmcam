import numpy as np
from PIL import Image

from filmlab.cli import main


def _make_frame(directory, index):
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(index)
    data = (rng.random((32, 48, 3)) * 200 + 20).astype(np.uint8)
    Image.fromarray(data).save(directory / f"FILM_{index:04d}.JPG", quality=95)
    (directory / f"FILM_{index:04d}.TXT").write_text(
        f"frame={index}\nmillis=800\nexposure=200\ngain=6\n"
        "awb_r=1\nawb_b=1\nframesize=UXGA\nquality=4\n"
    )


def test_stocks_command_lists_all_four(capsys):
    assert main(["stocks"]) == 0
    out = capsys.readouterr().out
    for stock_id in ("portra400", "cinestill800t", "hp5", "superia400"):
        assert stock_id in out


def test_develop_a_directory_writes_both_outputs(tmp_path):
    dcim = tmp_path / "DCIM"
    _make_frame(dcim, 1)
    _make_frame(dcim, 2)
    out_dir = tmp_path / "out"
    assert main(["develop", str(dcim), "--stock", "portra400", "--out", str(out_dir)]) == 0
    assert (out_dir / "FILM_0001.tif").exists()
    assert (out_dir / "FILM_0001.jpg").exists()
    assert (out_dir / "FILM_0002.tif").exists()


def test_develop_skips_already_developed_frames(tmp_path):
    dcim = tmp_path / "DCIM"
    _make_frame(dcim, 1)
    out_dir = tmp_path / "out"
    main(["develop", str(dcim), "--stock", "hp5", "--out", str(out_dir)])
    first = (out_dir / "FILM_0001.jpg").stat().st_mtime_ns
    main(["develop", str(dcim), "--stock", "hp5", "--out", str(out_dir)])
    assert (out_dir / "FILM_0001.jpg").stat().st_mtime_ns == first


def test_force_redevelops(tmp_path):
    dcim = tmp_path / "DCIM"
    _make_frame(dcim, 1)
    out_dir = tmp_path / "out"
    main(["develop", str(dcim), "--stock", "hp5", "--out", str(out_dir)])
    (out_dir / "FILM_0001.jpg").unlink()
    main(["develop", str(dcim), "--stock", "hp5", "--out", str(out_dir), "--force"])
    assert (out_dir / "FILM_0001.jpg").exists()


def test_a_corrupt_frame_does_not_abort_the_roll(tmp_path):
    dcim = tmp_path / "DCIM"
    _make_frame(dcim, 1)
    (dcim / "FILM_0002.JPG").write_bytes(b"not a jpeg")
    out_dir = tmp_path / "out"
    code = main(["develop", str(dcim), "--stock", "portra400", "--out", str(out_dir)])
    assert code == 1  # reports failure
    assert (out_dir / "FILM_0001.jpg").exists()  # but the good frame developed


def test_unknown_stock_is_a_usage_error(tmp_path):
    dcim = tmp_path / "DCIM"
    _make_frame(dcim, 1)
    assert main(["develop", str(dcim), "--stock", "velvia50", "--out", str(tmp_path / "o")]) == 2


def test_missing_input_path_is_a_usage_error(tmp_path):
    assert main(["develop", str(tmp_path / "nope"), "--stock", "hp5", "--out", str(tmp_path / "o")]) == 2
