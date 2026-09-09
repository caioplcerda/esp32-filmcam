"""The `filmlab` command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .contact import contact_sheet
from .io_jpeg import read_image, read_sidecar, write_jpeg, write_tiff
from .lut import load_cube
from .pipeline import DevelopOptions, develop
from .stocks import available_stocks, load_stock

EXIT_OK = 0
EXIT_FRAME_FAILED = 1
EXIT_USAGE = 2

_JPEG_SUFFIXES = {".jpg", ".jpeg", ".JPG", ".JPEG"}
_SHEET_NAME = "contact_sheet.jpg"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filmlab", description="Develop ESP32-CAM frames into film-like images."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dev = sub.add_parser("develop", help="develop a frame, a directory, or a card")
    dev.add_argument("input", help="JPEG file or directory of frames")
    dev.add_argument("--stock", required=True, help=f"one of: {', '.join(available_stocks())}")
    dev.add_argument("--out", required=True, help="output directory")
    dev.add_argument("--grain", type=float, default=1.0)
    dev.add_argument("--halation", type=float, default=1.0)
    dev.add_argument("--bloom", type=float, default=1.0)
    dev.add_argument("--vignette", type=float, default=1.0)
    dev.add_argument("--ca", type=float, default=1.0, help="chromatic aberration")
    dev.add_argument("--defocus", type=float, default=1.0)
    dev.add_argument("--lut", help="optional .cube LUT, used instead of the stock curves")
    dev.add_argument("--force", action="store_true", help="redevelop existing outputs")

    sub.add_parser("stocks", help="list available film stocks")

    con = sub.add_parser("contact", help="render a contact sheet from developed JPEGs")
    con.add_argument("input", help="directory of developed frames")
    con.add_argument("--columns", type=int, default=4)

    return parser


def _frames_in(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.suffix in _JPEG_SUFFIXES)


def _cmd_stocks() -> int:
    for stock_id in available_stocks():
        print(f"{stock_id:16s} {load_stock(stock_id).name}")
    return EXIT_OK


def _cmd_develop(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.exists():
        print(f"error: no such path: {source}", file=sys.stderr)
        return EXIT_USAGE
    try:
        stock = load_stock(args.stock)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    lut = None
    if args.lut:
        try:
            lut = load_cube(Path(args.lut))
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE

    options = DevelopOptions(
        grain=args.grain,
        halation=args.halation,
        bloom=args.bloom,
        vignette=args.vignette,
        ca=args.ca,
        defocus=args.defocus,
        lut=lut,
    )

    frames = _frames_in(source)
    if not frames:
        print(f"error: no JPEG frames found in {source}", file=sys.stderr)
        return EXIT_USAGE

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for frame_path in frames:
        jpg_out = out_dir / f"{frame_path.stem}.jpg"
        tif_out = out_dir / f"{frame_path.stem}.tif"
        if not args.force and jpg_out.exists() and tif_out.exists():
            print(f"skip  {frame_path.name} (already developed)")
            continue
        try:
            img = read_image(frame_path)
            meta = read_sidecar(frame_path.with_suffix(".TXT"))
            out = develop(img, stock, meta, options)
            write_tiff(tif_out, out)
            write_jpeg(jpg_out, out)
        except Exception as exc:  # one bad frame must not kill the roll
            failures += 1
            print(f"FAIL  {frame_path.name}: {exc}", file=sys.stderr)
            continue
        print(f"ok    {frame_path.name} -> {jpg_out.name}")

    if failures:
        print(f"{failures} frame(s) failed", file=sys.stderr)
        return EXIT_FRAME_FAILED
    return EXIT_OK


def _cmd_contact(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.is_dir():
        print(f"error: not a directory: {source}", file=sys.stderr)
        return EXIT_USAGE
    frames = [p for p in _frames_in(source) if p.name != _SHEET_NAME]
    if not frames:
        print(f"error: no developed frames in {source}", file=sys.stderr)
        return EXIT_USAGE

    images = [read_image(p) for p in frames]
    labels = [p.stem.replace("FILM_", "") for p in frames]
    sheet = contact_sheet(images, labels, columns=args.columns)
    out_path = source / _SHEET_NAME
    write_jpeg(out_path, sheet)
    print(f"ok    {out_path}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "stocks":
        return _cmd_stocks()
    if args.command == "develop":
        return _cmd_develop(args)
    return _cmd_contact(args)


if __name__ == "__main__":
    raise SystemExit(main())
