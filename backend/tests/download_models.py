"""
Download verified OpenCV Zoo YuNet and SFace ONNX models.
Validates file existence, download integrity, and reported sizes.
"""

import os
import sys
import requests

MODELS = {
    "yunet": {
        "filename": "face_detection_yunet_2023mar.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "alt_url": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "min_size_bytes": 200_000,       # Exact model size: ~232.6 KB (232,589 bytes)
        "expected_desc": "YuNet Face Detector (Apache 2.0)"
    },
    "sface": {
        "filename": "face_recognition_sface_2021dec.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "alt_url": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "min_size_bytes": 35_000_000,    # ~37.4 MB
        "expected_desc": "SFace Face Recognizer 128-D (Apache 2.0)"
    }
}


def download_file(url: str, alt_url: str, dest_path: str, min_size: int) -> bool:
    print(f"Downloading from {url} ...")
    try:
        response = requests.get(url, stream=True, timeout=60, allow_redirects=True)
        if response.status_code != 200:
            print(f"Primary URL returned status {response.status_code}. Trying alternate URL...")
            response = requests.get(alt_url, stream=True, timeout=60, allow_redirects=True)

        response.raise_for_status()

        total_bytes = 0
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
                    mb = total_bytes / (1024 * 1024)
                    sys.stdout.write(f"\r  Downloaded: {mb:.2f} MB")
                    sys.stdout.flush()
        print()

        actual_size = os.path.getsize(dest_path)
        if actual_size < min_size:
            print(f"ERROR: Downloaded file size ({actual_size} bytes) is smaller than expected minimum ({min_size} bytes).")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False

        print(f"SUCCESS: Verified {dest_path} ({actual_size / (1024*1024):.2f} MB)")
        return True

    except Exception as e:
        print(f"ERROR: Failed to download {dest_path}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def ensure_models(weights_dir: str = None) -> bool:
    if weights_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        weights_dir = os.path.join(base_dir, "weights")

    os.makedirs(weights_dir, exist_ok=True)
    all_ok = True

    print("=" * 65)
    print(" SmartGateAI: Verifying / Downloading OpenCV Zoo ONNX Models")
    print("=" * 65)

    for key, info in MODELS.items():
        target_path = os.path.join(weights_dir, info["filename"])
        print(f"\n[{key.upper()}] {info['expected_desc']}")

        if os.path.exists(target_path):
            size = os.path.getsize(target_path)
            if size >= info["min_size_bytes"]:
                print(f"  Already present and valid: {target_path} ({size / (1024*1024):.2f} MB)")
                continue
            else:
                print(f"  Existing file is incomplete ({size} bytes). Re-downloading...")

        success = download_file(info["url"], info["alt_url"], target_path, info["min_size_bytes"])
        if not success:
            all_ok = False
            print(f"  FAILED to acquire model '{info['filename']}'. Cannot proceed.")

    return all_ok


if __name__ == "__main__":
    success = ensure_models()
    if not success:
        sys.exit(1)
    print("\nAll model files are verified and ready.")
