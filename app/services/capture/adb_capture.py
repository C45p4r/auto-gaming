import subprocess
from io import BytesIO

from PIL import Image

from app.config import settings


class AdbCaptureError(RuntimeError):
    pass


def adb_exec(args: list[str], timeout: float = 10.0) -> bytes:
    cmd = [settings.adb_path] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)
    except subprocess.CalledProcessError as exc:
        raise AdbCaptureError(exc.stderr.decode("utf-8", errors="ignore")) from exc
    except subprocess.TimeoutExpired as exc:
        raise AdbCaptureError(f"ADB command timed out: {' '.join(cmd)}") from exc
    return proc.stdout


def get_connected_device(serial: str | None = None) -> str | None:
    out = adb_exec(["devices"]).decode("utf-8", errors="ignore")
    lines = [line.strip() for line in out.splitlines() if "\tdevice" in line]
    devices = [line.split("\t")[0] for line in lines]
    if not devices:
        return None
    if serial and serial in devices:
        return serial
    return devices[0]


def capture_frame(serial: str | None = None) -> Image.Image:
    device = get_connected_device(serial)
    if not device:
        raise AdbCaptureError("No ADB device connected. Start an emulator or connect a device.")
    raw = adb_exec(["-s", device, "exec-out", "screencap -p"], timeout=20.0)
    return Image.open(BytesIO(raw)).convert("RGB")
