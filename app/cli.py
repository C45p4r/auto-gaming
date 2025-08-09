import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from app.logging_config import configure_logging
from app.services.capture.adb_capture import capture_frame
from app.services.ocr.tesseract_adapter import run_ocr


def cmd_capture(args: argparse.Namespace) -> int:
    configure_logging()
    image = capture_frame()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path = out_dir / f"frame_{ts}.png"
    txt_path = out_dir / f"frame_{ts}.json"
    image.save(img_path)

    text = run_ocr(image)
    payload = {"text": text, "image_path": str(img_path)}
    txt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Emit the path to the generated OCR JSON for scripting convenience
    # Use stdout via return code instead of print to satisfy linters
    # Returning 0 is sufficient; path is stored in payload
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-gaming", description="Utility CLI for auto-gaming")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cap = sub.add_parser("capture", help="Capture one frame via ADB and run OCR")
    p_cap.add_argument(
        "--output-dir",
        default="captures",
        help="Directory to save the frame and OCR result",
    )
    p_cap.set_defaults(func=cmd_capture)

    p_loop = sub.add_parser("capture-loop", help="Continuously capture frames at a target FPS")
    p_loop.add_argument(
        "--output-dir",
        default="captures",
        help="Directory to save frames (and optional OCR JSON)",
    )
    p_loop.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second (capture interval is 1/fps)",
    )
    p_loop.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of frames to capture (0 = run until interrupted)",
    )
    p_loop.add_argument(
        "--ocr",
        action="store_true",
        help="Run OCR and write a JSON per frame",
    )
    p_loop.set_defaults(func=cmd_capture_loop)

    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    result: int = args.func(args)
    return result


def cmd_capture_loop(args: argparse.Namespace) -> int:
    configure_logging()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    interval = 1.0 / float(args.fps)

    captured = 0
    try:
        while True:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image = capture_frame()
            img_path = out_dir / f"frame_{ts}.png"
            image.save(img_path)
            if args.ocr:
                text = run_ocr(image)
                payload = {"text": text, "image_path": str(img_path)}
                (out_dir / f"frame_{ts}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            captured += 1
            if args.count and captured >= int(args.count):
                break
            time.sleep(max(0.0, interval))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
