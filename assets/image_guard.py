"""
image_guard.py  — Mandatory pre-flight image integrity check.
Canonical values updated for input_source_image_research.png (Iteration 9+).
"""
import hashlib, json, os, sys
import numpy as np
from PIL import Image

CANONICAL = {
    "file_sha256":  "144042ebd969acf6ecd3617b8a6e39cfe07164b49937d7188ca390908ffddff7",
    "file_md5":     "45e4107b11444116aa72de7467a23f48",
    "file_size":    116236,
    # Pixel hash at time of retrieving from claude 
    #"pixel_sha256": "6e4f7056f0a6023f5b3bcaadef342ed076d929f05f33faccdfe037bc2b27c9b4",

    "pixel_sha256": "76d02c13e19435bd277a7ee52a7da806bd3d8aeb2b8ed64f9163a78f863867de",
    "pixel_shape":  (1024, 831, 3),
    "pixel_dtype":  "uint8",
    "pixel_mean":   231.403371,
    "pixel_std":    63.732681,
    "pixel_min":    0,
    "pixel_max":    255,
    "invert":       True,
}
_MEAN_TOL = 0.01
_STD_TOL  = 0.01
DEFAULT_IMG_PATH = "assets/input_source_image.png"
ALLOW_NONCANONICAL_ENV = "MINESTREAKER_ALLOW_NONCANONICAL"


def _env_flag_enabled(name: str) -> bool:
    val = os.getenv(name, "").strip().lower()
    return val in ("1", "true", "yes", "on")

def verify_source_image(path=DEFAULT_IMG_PATH, halt_on_failure=True, verbose=True):
    failures = []
    allow_noncanonical = _env_flag_enabled(ALLOW_NONCANONICAL_ENV)
    def _fail(msg):
        failures.append(msg)
        if verbose: print(f"  X FAIL: {msg}")
    def _ok(msg):
        if verbose: print(f"  OK {msg}")
    if verbose:
        print("="*60); print("IMAGE INTEGRITY VERIFICATION"); print("="*60)
        print(f"  Checking: {path}\n")
    if not os.path.exists(path):
        _fail(f"File not found: {path}")
        return _handle_failure(failures, halt_on_failure, verbose)
    actual_size = os.path.getsize(path)
    if allow_noncanonical:
        _ok(f"File size: {actual_size:,} bytes (non-canonical mode)")
    elif actual_size != CANONICAL["file_size"]:
        _fail(f"File size mismatch: expected {CANONICAL['file_size']:,}, got {actual_size:,}")
    else:
        _ok(f"File size: {actual_size:,} bytes")
    try:
        img = Image.open(path); arr = np.array(img, dtype=np.uint8)
    except Exception as e:
        _fail(f"Failed to open/decode image: {e}")
        return _handle_failure(failures, halt_on_failure, verbose)
    if allow_noncanonical:
        if arr.ndim not in (2, 3):
            _fail(f"Unsupported image rank: expected 2D/3D array, got ndim={arr.ndim}")
        else:
            _ok(f"Decoded image rank: ndim={arr.ndim}")
        if arr.ndim == 3 and arr.shape[2] not in (1, 3, 4):
            _fail(f"Unsupported channel count: expected 1/3/4, got {arr.shape[2]}")
        elif arr.ndim == 3:
            _ok(f"Channel count: {arr.shape[2]}")
        if arr.dtype != np.uint8:
            _fail(f"Unexpected dtype: expected uint8, got {arr.dtype}")
        else:
            _ok(f"Pixel dtype: {arr.dtype}")
        if arr.size == 0:
            _fail("Decoded image contains no pixels")
        else:
            _ok(f"Pixel count: {arr.size:,}")
        if verbose:
            print(f"  WARN {ALLOW_NONCANONICAL_ENV}=1 set; canonical hash checks bypassed")
        return _handle_failure(failures, halt_on_failure, verbose)
    if arr.shape != tuple(CANONICAL["pixel_shape"]):
        _fail(f"Shape mismatch: expected {CANONICAL['pixel_shape']}, got {arr.shape}")
    else:
        _ok(f"Shape: {arr.shape}")
    actual_mean = float(arr.mean()); actual_std = float(arr.std())
    actual_min = int(arr.min()); actual_max = int(arr.max())
    if abs(actual_mean - CANONICAL["pixel_mean"]) > _MEAN_TOL:
        _fail(f"Pixel mean mismatch: expected {CANONICAL['pixel_mean']:.6f}, got {actual_mean:.6f}")
    else:
        _ok(f"Pixel mean: {actual_mean:.6f}")
    if abs(actual_std - CANONICAL["pixel_std"]) > _STD_TOL:
        _fail(f"Pixel std mismatch: expected {CANONICAL['pixel_std']:.6f}, got {actual_std:.6f}")
    else:
        _ok(f"Pixel std:  {actual_std:.6f}")
    if actual_min != CANONICAL["pixel_min"] or actual_max != CANONICAL["pixel_max"]:
        _fail(f"Pixel range mismatch: expected [{CANONICAL['pixel_min']},{CANONICAL['pixel_max']}], got [{actual_min},{actual_max}]")
    else:
        _ok(f"Pixel range: [{actual_min}, {actual_max}]")
    with open(path, "rb") as f: raw = f.read()
    file_sha256 = hashlib.sha256(raw).hexdigest()
    if file_sha256 != CANONICAL["file_sha256"]:
        if verbose: print("  WARN File SHA256 differs (checking pixels)")
    else:
        _ok(f"File SHA256: {file_sha256[:16]}...")
    pixel_sha256 = hashlib.sha256(arr.tobytes()).hexdigest()
    if pixel_sha256 != CANONICAL["pixel_sha256"]:
        _fail(f"PIXEL SHA256 MISMATCH\n  Expected: {CANONICAL['pixel_sha256']}\n  Got:      {pixel_sha256}")
    else:
        _ok(f"Pixel SHA256: {pixel_sha256[:16]}... AUTHORITATIVE MATCH")
    return _handle_failure(failures, halt_on_failure, verbose)

def _handle_failure(failures, halt_on_failure, verbose):
    if not failures:
        if verbose:
            print("\n  ALL CHECKS PASSED - source image is verified authentic")
            print("="*60+"\n")
        return True
    if verbose:
        print(f"\n  IMAGE VERIFICATION FAILED - {len(failures)} check(s) failed\n")
    if halt_on_failure: sys.exit(1)
    return False

def get_canonical_record(): return dict(CANONICAL)

def compute_image_hashes(path):
    with open(path,"rb") as f: raw=f.read()
    img=Image.open(path); arr=np.array(img,dtype=np.uint8)
    return {"path":path,"file_size":len(raw),"file_md5":hashlib.md5(raw).hexdigest(),
            "file_sha256":hashlib.sha256(raw).hexdigest(),
            "pixel_sha256":hashlib.sha256(arr.tobytes()).hexdigest(),
            "pixel_shape":arr.shape,"pixel_dtype":str(arr.dtype),
            "pixel_mean":float(arr.mean()),"pixel_std":float(arr.std()),
            "pixel_min":int(arr.min()),"pixel_max":int(arr.max())}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--path",default=DEFAULT_IMG_PATH)
    p.add_argument("--compute",action="store_true"); args=p.parse_args()
    if args.compute: print(json.dumps(compute_image_hashes(args.path),indent=2))
    else:
        ok=verify_source_image(args.path,halt_on_failure=True)
        sys.exit(0 if ok else 1)
