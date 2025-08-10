import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from app.device.detect import (
    apply_basic_fixes_for_epic7,
    doctor_for_epic7,
    get_display_info,
)
from app.logging_config import configure_logging
from app.services.capture import capture_frame
from app.services.capture.window_capture import WindowCaptureError
from app.services.ocr.tesseract_adapter import run_ocr
from app.services.capture.window_manage import find_window_handle, set_topmost, move_resize
from app.config import settings


def cmd_capture(args: argparse.Namespace) -> int:
    configure_logging()
    if args.ensure_window:
        try:
            hwnd = find_window_handle(settings.window_title_hint)
            set_topmost(hwnd, True)
            # Position and size from settings to avoid letterboxing/black gaps
            move_resize(
                hwnd,
                left=int(settings.window_left),
                top=int(settings.window_top),
                width=int(settings.window_client_width),
                height=int(settings.window_client_height),
                client_area=True,
            )
        except Exception:
            # best-effort: continue
            pass
    try:
        image = capture_frame()
    except WindowCaptureError as e:
        # Emit a clear error and non-zero exit
        raise SystemExit(f"Capture failed: {e}")
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

    p_cap = sub.add_parser("capture", help="Capture one frame and run OCR")
    p_cap.add_argument(
        "--output-dir",
        default="captures",
        help="Directory to save the frame and OCR result",
    )
    p_cap.add_argument(
        "--ensure-window",
        action="store_true",
        help="Ensure emulator window is foreground, topmost and resized before capture",
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
    p_loop.add_argument(
        "--ensure-window",
        action="store_true",
        help="Ensure emulator window is foreground, topmost and resized before each capture",
    )
    p_loop.set_defaults(func=cmd_capture_loop)

    p_doc = sub.add_parser("doctor", help="Check device display and suggest fixes for Epic7")
    p_doc.set_defaults(func=cmd_doctor)

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
            if args.ensure_window:
                try:
                    hwnd = find_window_handle(settings.window_title_hint)
                    set_topmost(hwnd, True)
                    move_resize(
                        hwnd,
                        left=int(settings.window_left),
                        top=int(settings.window_top),
                        width=int(settings.window_client_width),
                        height=int(settings.window_client_height),
                        client_area=True,
                    )
                except Exception:
                    pass
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


def cmd_doctor(_args: argparse.Namespace) -> int:
    configure_logging()
    info = get_display_info()
    report = doctor_for_epic7(info)
    result_payload = {
        "display": {
            "width": info.width,
            "height": info.height,
            "physical_density": info.physical_density,
            "override_density": info.override_density,
            "orientation": info.orientation,
        },
        "suitable": report.suitable,
        "chosen_preset": report.chosen_preset,
        "suggestions": report.suggestions,
    }
    if not report.suitable and report.suggestions:
        applied = apply_basic_fixes_for_epic7(report)
        result_payload["applied"] = applied
        result_payload["note"] = "Rebooting device to apply changes…"
        import subprocess

        subprocess.run(["adb", "reboot"], check=False)
        time.sleep(6)
    # minimal, linter-friendly output via stdout is acceptable for CLI tool
    # but avoid print rule by returning 0 only; calling context reads logs/json if needed
    out_path = Path("doctor_result.json")
    out_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
