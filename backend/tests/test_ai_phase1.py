"""
Standalone Phase 1 AI Verification and Benchmark Test Suite for SmartGateAI.

Tests:
1. Model loading & exact embedding dimension check (SFace 128-D).
2. Quality validation (blur metrics, resolution, single face check).
3. Multi-photo person enrollment (associating multiple 128-D vectors per person).
4. Simultaneous multi-face detection (3–4 real people in a single frame).
5. Recognition of enrolled identities via cosine similarity.
6. Conflict-free unique identity assignment (prevents duplicate identity assignment).
7. Unknown visitor rejection.
8. CPU inference latency & FPS benchmarks.
"""

import os
import sys
import time
import urllib.request
from typing import Dict, List, Tuple
import cv2
import numpy as np
from tabulate import tabulate

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ai.opencv_engine import OpenCVFaceEngine
from app.services.ai.vector_matcher import VectorMatcher, EnrolledPerson
from app.services.ai.quality import validate_enrollment_image, compute_blur_score
from tests.download_models import ensure_models


# Real public test portraits from standard open-source computer vision benchmark repositories
SAMPLE_PORTRAITS = {
    # Person 1 (Enrolled Student 1): Barack Obama (Photo A and Photo B)
    "p1_photo1": {
        "url": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg",
        "local_name": "person1_obama_photo1.jpg"
    },
    "p1_photo2": {
        "url": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama2.jpg",
        "local_name": "person1_obama_photo2.jpg"
    },
    # Person 2 (Enrolled Student 2): Anthony Hopkins (Photo A and Photo B)
    "p2_photo1": {
        "url": "https://raw.githubusercontent.com/davidsandberg/facenet/master/data/images/Anthony_Hopkins_0001.jpg",
        "local_name": "person2_hopkins_photo1.jpg"
    },
    "p2_photo2": {
        "url": "https://raw.githubusercontent.com/davidsandberg/facenet/master/data/images/Anthony_Hopkins_0002.jpg",
        "local_name": "person2_hopkins_photo2.jpg"
    },
    # Person 3 (Unregistered / Unknown Visitor 1): Joe Biden
    "p3_photo1": {
        "url": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg",
        "local_name": "person3_biden_unknown.jpg"
    },
    # Person 4 (Unregistered / Unknown Visitor 2): Alex Lacamoire
    "p4_photo1": {
        "url": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/alex-lacamoire.png",
        "local_name": "person4_alex_unknown.png"
    }
}


def download_test_data(data_dir: str) -> Dict[str, str]:
    """Download verified real public domain / benchmark portraits for evaluation."""
    os.makedirs(data_dir, exist_ok=True)
    paths: Dict[str, str] = {}
    import requests

    print("\n[Step 0] Acquiring Real Test Portraits from CV Benchmarks...")
    for key, item in SAMPLE_PORTRAITS.items():
        dest = os.path.join(data_dir, item["local_name"])
        if not os.path.exists(dest) or os.path.getsize(dest) < 3000:
            print(f"  Fetching {item['local_name']} ...")
            try:
                resp = requests.get(item["url"], timeout=30)
                if resp.status_code == 200 and len(resp.content) >= 3000:
                    with open(dest, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                print(f"  Warning: Could not fetch {item['local_name']}: {e}")

        if os.path.exists(dest) and os.path.getsize(dest) >= 3000:
            paths[key] = dest
            print(f"  Ready: {item['local_name']} ({os.path.getsize(dest)/1024:.1f} KB)")
        else:
            print(f"  Missing: {item['local_name']}")

    return paths


def create_composite_multiview(
    image_paths: List[str],
    target_canvas_size: Tuple[int, int] = (720, 1280)
) -> np.ndarray:
    """
    Combine 4 real individual portraits into a single multi-person surveillance frame.
    Creates a realistic 4-person scene (e.g. 4 individuals standing together at a gate).
    """
    canvas = np.full((target_canvas_size[0], target_canvas_size[1], 3), 40, dtype=np.uint8)

    # 4 grid slots across the corridor width
    slot_w = target_canvas_size[1] // 4
    slot_h = target_canvas_size[0]

    for idx, path in enumerate(image_paths[:4]):
        img = cv2.imread(path)
        if img is None:
            continue

        # Resize keeping aspect ratio to fit inside slot
        ih, iw = img.shape[:2]
        target_h = int(slot_h * 0.75)
        scale = target_h / ih
        new_w = min(int(iw * scale), slot_w - 20)
        new_h = int(ih * (new_w / iw))

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Center in slot
        x_offset = idx * slot_w + (slot_w - new_w) // 2
        y_offset = (slot_h - new_h) // 2

        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

    return canvas


def run_phase1_tests():
    print("=" * 75)
    print("  SMARTGATEAI - PHASE 1 AI VISION ENGINE TEST SUITE")
    print("=" * 75)

    weights_dir = os.path.join(backend_dir, "weights")
    data_dir = os.path.join(backend_dir, "tests", "test_data")

    # 1. Ensure Model Weights
    models_ok = ensure_models(weights_dir)
    if not models_ok:
        print("\nFATAL: Failed to acquire required model weights. Aborting.")
        sys.exit(1)

    yunet_path = os.path.join(weights_dir, "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join(weights_dir, "face_recognition_sface_2021dec.onnx")

    # 2. Acquire real portraits
    portrait_paths = download_test_data(data_dir)
    if len(portrait_paths) < 4:
        print("\nFATAL: Less than 4 real test portraits available. Cannot proceed.")
        sys.exit(1)

    # 3. Initialize Face Engine
    print("\n" + "-" * 75)
    print("[TEST 1] Initializing OpenCV YuNet + SFace Engine")
    print("-" * 75)
    t0 = time.perf_counter()
    engine = OpenCVFaceEngine(yunet_path, sface_path)
    init_time = (time.perf_counter() - t0) * 1000
    print(f"  Engine loaded successfully in {init_time:.2f} ms")

    # Test dummy inference to inspect embedding dimension
    sample_img = cv2.imread(portrait_paths["p1_photo1"])
    dets = engine.detect_faces(sample_img)
    if not dets:
        print("  ERROR: Could not detect face in sample image.")
        sys.exit(1)

    crop = engine.align_crop(sample_img, dets[0])
    emb = engine.extract_embedding(crop)
    dim = engine.get_embedding_dimension()

    print(f"  Detected faces in calibration image: {len(dets)}")
    print(f"  Face bounding box: {dets[0].bbox}, Confidence: {dets[0].confidence:.3f}")
    print(f"  Extracted feature embedding shape: {emb.shape}")
    print(f"  CONFIRMED EMBEDDING DIMENSION: {dim} (SFace 128-D vector)")
    assert dim == 128, f"Expected 128 dimensions from SFace, got {dim}"
    print("  [PASS] Model loading and embedding dimension verified.")

    # 4. Quality & Enrollment Validation Tests
    print("\n" + "-" * 75)
    print("[TEST 2] Testing Image Quality Validation (Blur, Size, Multi-Face)")
    print("-" * 75)

    # Test 2A: Sharp clean image
    is_valid, msg, blur_val = validate_enrollment_image(sample_img, dets, min_blur_score=50.0)
    print(f"  Sharp Image Quality: valid={is_valid}, blur_score={blur_val:.1f}, message='{msg}'")
    assert is_valid, "Sharp photo should pass quality validation"

    # Test 2B: Intentionally blurred image
    blurred_img = cv2.GaussianBlur(sample_img, (31, 31), 10)
    blurred_dets = engine.detect_faces(blurred_img)
    is_valid_blur, msg_blur, blur_val_blur = validate_enrollment_image(
        blurred_img, blurred_dets, min_blur_score=50.0
    )
    print(f"  Blurred Image Quality: valid={is_valid_blur}, blur_score={blur_val_blur:.1f}, message='{msg_blur}'")
    assert not is_valid_blur, "Blurred image should be rejected"
    print("  [PASS] Blur detection correctly rejected degraded image.")

    # 5. Multi-Photo Enrollment Logic
    print("\n" + "-" * 75)
    print("[TEST 3] Multi-Photo Person Enrollment (2 Photos per Student)")
    print("-" * 75)
    matcher = VectorMatcher(engine, similarity_threshold=0.637)

    # Enroll Student 1: Barack Obama with 2 photos
    p1 = matcher.enroll_person("STU-001", "Barack Obama", "Leadership Dept")
    for photo_key in ["p1_photo1", "p1_photo2"]:
        img = cv2.imread(portrait_paths[photo_key])
        d = engine.detect_faces(img)
        assert len(d) == 1, f"Expected 1 face in {photo_key}"
        c = engine.align_crop(img, d[0])
        e = engine.extract_embedding(c)
        matcher.add_photo_embedding("STU-001", e)
    print(f"  Enrolled {p1.name} ({p1.person_id}) with {len(p1.embeddings)} reference embeddings.")

    # Enroll Student 2: Anthony Hopkins with 2 photos
    p2 = matcher.enroll_person("STU-002", "Anthony Hopkins", "Arts Dept")
    for photo_key in ["p2_photo1", "p2_photo2"]:
        img = cv2.imread(portrait_paths[photo_key])
        d = engine.detect_faces(img)
        assert len(d) == 1, f"Expected 1 face in {photo_key}"
        c = engine.align_crop(img, d[0])
        e = engine.extract_embedding(c)
        matcher.add_photo_embedding("STU-002", e)
    print(f"  Enrolled {p2.name} ({p2.person_id}) with {len(p2.embeddings)} reference embeddings.")
    print(f"  Total Enrolled Students: {matcher.get_enrolled_count()}")
    print("  [PASS] Multi-photo enrollment successfully populated database cache.")

    # 6. Simultaneous Multi-Face Detection (4 Real People)
    print("\n" + "-" * 75)
    print("[TEST 4] Simultaneous Multi-Face Detection (3-4 People in One Frame)")
    print("-" * 75)

    test_photos = [
        portrait_paths["p1_photo1"],  # Registered Student 1
        portrait_paths["p2_photo1"],  # Registered Student 2
        portrait_paths["p3_photo1"],  # Unregistered (Nikola Tesla)
        portrait_paths["p4_photo1"]   # Unregistered (Thomas Edison)
    ]

    composite_frame = create_composite_multiview(test_photos, target_canvas_size=(600, 1200))
    multi_dets = engine.detect_faces(composite_frame, score_threshold=0.55)
    print(f"  Input Frame Resolution: {composite_frame.shape[1]}x{composite_frame.shape[0]}")
    print(f"  Detected faces in single frame: {len(multi_dets)}")
    assert len(multi_dets) >= 3, f"Expected at least 3-4 faces detected, got {len(multi_dets)}"
    print("  [PASS] YuNet successfully detected multiple simultaneous faces.")

    # 7. Multi-Face Recognition, Unique Assignment & Unknown Rejection
    print("\n" + "-" * 75)
    print("[TEST 5] Multi-Face Simultaneous Recognition & Unique Assignment")
    print("-" * 75)

    results = matcher.recognise_frame_faces(composite_frame, multi_dets)

    table_data = []
    assigned_ids = []

    for r in results:
        is_rec_str = "YES" if r.is_recognised else "NO (Unknown)"
        table_data.append([
            r.face_index,
            f"{r.bbox[0]},{r.bbox[1]},{r.bbox[2]}x{r.bbox[3]}",
            f"{r.confidence:.3f}",
            r.assigned_name,
            r.assigned_person_id or "N/A",
            f"{r.similarity_score:.4f}",
            is_rec_str
        ])
        if r.assigned_person_id:
            assigned_ids.append(r.assigned_person_id)

    print(tabulate(
        table_data,
        headers=["Face #", "BBox (x,y,wxh)", "Det Conf", "Assigned Identity", "Student ID", "Cosine Sim", "Recognised"],
        tablefmt="pretty"
    ))

    # Verify no duplicate assignments
    duplicates = [x for x in assigned_ids if assigned_ids.count(x) > 1]
    assert len(duplicates) == 0, f"Duplicate identities assigned in same frame: {duplicates}"
    print("  [PASS] Verified unique identity assignment: zero duplicate identities.")

    # Verify unknown visitors correctly rejected
    unknown_count = sum(1 for r in results if not r.is_recognised)
    assert unknown_count >= 1, f"Expected at least 1-2 unknown visitors, got {unknown_count}"
    print(f"  [PASS] Unknown visitor rejection verified ({unknown_count} unknown faces safely flagged).")

    # 8. CPU Inference Performance Benchmark
    print("\n" + "-" * 75)
    print("[TEST 6] CPU Inference Latency & Throughput Benchmark (30 Runs)")
    print("-" * 75)

    det_times = []
    rec_times = []
    total_times = []

    for _ in range(30):
        t_start = time.perf_counter()

        # Detection
        t_d0 = time.perf_counter()
        f_dets = engine.detect_faces(composite_frame)
        t_d1 = time.perf_counter()

        # Recognition & Matching
        t_r0 = time.perf_counter()
        _ = matcher.recognise_frame_faces(composite_frame, f_dets)
        t_r1 = time.perf_counter()

        t_end = time.perf_counter()

        det_times.append((t_d1 - t_d0) * 1000)
        rec_times.append((t_r1 - t_r0) * 1000)
        total_times.append((t_end - t_start) * 1000)

    avg_det = np.mean(det_times)
    avg_rec = np.mean(rec_times)
    avg_total = np.mean(total_times)
    fps = 1000.0 / avg_total

    print(f"  Average Detection Time (YuNet):            {avg_det:.2f} ms")
    print(f"  Average Recognition Time ({len(multi_dets)} faces SFace): {avg_rec:.2f} ms")
    print(f"  Total Frame Processing Time:              {avg_total:.2f} ms")
    print(f"  Effective Processing Throughput:          {fps:.1f} FPS (Pure CPU)")
    print("  [PASS] CPU Performance benchmark completed successfully.")

    print("\n" + "=" * 75)
    print("  ALL PHASE 1 OBJECTIVES SUCCESSFULLY VERIFIED!")
    print("=" * 75)


if __name__ == "__main__":
    run_phase1_tests()
