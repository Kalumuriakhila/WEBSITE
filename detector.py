"""Deepfake video analysis pipeline using OpenCV and neural/forensic scoring."""

import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Optional TensorFlow/Keras model support if a custom trained model is provided
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "deepfake_detector.keras"
)
_LOADED_MODEL: Optional[Any] = None


def _get_keras_model() -> Optional[Any]:
    """Load a custom Keras deepfake model if present on disk."""
    global _LOADED_MODEL
    if _LOADED_MODEL is not None:
        return _LOADED_MODEL
    if os.path.exists(MODEL_PATH):
        try:
            import tensorflow as tf

            _LOADED_MODEL = tf.keras.models.load_model(MODEL_PATH)
            return _LOADED_MODEL
        except Exception:
            return None
    return None


def _load_face_cascade() -> cv2.CascadeClassifier:
    """Load OpenCV's bundled Haar cascade for frontal face detection."""
    cascade_path = os.path.join(
        cv2.data.haarcascades, "haarcascade_frontalface_default.xml"
    )
    return cv2.CascadeClassifier(cascade_path)


def _compute_frame_forensics(
    frame_bgr: np.ndarray,
    face_box: Optional[Tuple[int, int, int, int]],
) -> Tuple[float, float]:
    """Compute sharpness (Laplacian variance) and high-frequency DCT anomaly score."""
    if face_box is not None:
        x, y, w, h = face_box
        roi = frame_bgr[max(0, y) : y + h, max(0, x) : x + w]
    else:
        roi = frame_bgr

    if roi.size == 0:
        roi = frame_bgr

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128)).astype(np.float32)

    # 1. Edge / blending boundary sharpness via Laplacian variance
    laplacian_var = float(cv2.Laplacian(resized, cv2.CV_32F).var())

    # 2. High-frequency spectral energy ratio via 2D DCT
    dct = cv2.dct(resized / 255.0)
    total_energy = float(np.sum(np.abs(dct)) + 1e-6)
    high_freq_energy = float(np.sum(np.abs(dct[64:, 64:])))
    hf_ratio = high_freq_energy / total_energy

    return laplacian_var, hf_ratio


def analyze_video(
    video_path: str,
    frames_output_dir: str,
    scan_prefix: str,
    max_samples: int = 16,
) -> Dict[str, Any]:
    """
    Sample frames from a video, detect faces, extract forensic metrics,
    and classify the video as REAL or FAKE with a confidence score.
    """
    os.makedirs(frames_output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Unable to open video file. Please upload a valid video.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
    duration_seconds = round(total_frames / fps, 2) if total_frames > 0 else 0.0

    if total_frames <= 0:
        # Fallback: read sequentially up to max_samples * 5 frames
        sampled_indices = list(range(0, max_samples * 5, 5))
    else:
        count = min(max_samples, max(1, total_frames))
        sampled_indices = np.linspace(0, max(0, total_frames - 1), num=count, dtype=int).tolist()

    face_cascade = _load_face_cascade()
    keras_model = _get_keras_model()

    lap_scores: List[float] = []
    hf_scores: List[float] = []
    frame_diffs: List[float] = []
    model_fake_probs: List[float] = []
    saved_frame_urls: List[str] = []

    prev_gray_small: Optional[np.ndarray] = None
    faces_detected = 0
    frames_analyzed = 0

    for idx_pos, frame_idx in enumerate(sampled_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        frames_analyzed += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (160, 90))

        if prev_gray_small is not None:
            diff = float(np.mean(np.abs(small_gray.astype(np.float32) - prev_gray_small.astype(np.float32))))
            frame_diffs.append(diff)
        prev_gray_small = small_gray

        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(48, 48)
        )
        face_box: Optional[Tuple[int, int, int, int]] = None
        if len(faces) > 0:
            faces_detected += 1
            # Pick largest detected face
            fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
            face_box = (int(fx), int(fy), int(fw), int(fh))

        lap_var, hf_ratio = _compute_frame_forensics(frame, face_box)
        lap_scores.append(lap_var)
        hf_scores.append(hf_ratio)

        # If a custom Keras model is loaded, run inference on the face/frame crop
        if keras_model is not None:
            if face_box is not None:
                x, y, w, h = face_box
                crop = frame[max(0, y) : y + h, max(0, x) : x + w]
            else:
                crop = frame
            rgb_crop = cv2.cvtColor(cv2.resize(crop, (128, 128)), cv2.COLOR_BGR2RGB)
            tensor = np.expand_dims(rgb_crop.astype(np.float32) / 255.0, axis=0)
            pred = float(keras_model.predict(tensor, verbose=0)[0][0])
            model_fake_probs.append(pred)

        # Save up to 4 annotated sample frames for the Result page
        if len(saved_frame_urls) < 4 and (idx_pos % max(1, len(sampled_indices) // 4) == 0):
            annotated = frame.copy()
            if face_box is not None:
                x, y, w, h = face_box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 229, 255), 2)
                cv2.putText(
                    annotated,
                    "Face ROI",
                    (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 229, 255),
                    2,
                )
            thumb = cv2.resize(annotated, (320, 180))
            frame_filename = f"{scan_prefix}_frame_{len(saved_frame_urls) + 1}.jpg"
            cv2.imwrite(os.path.join(frames_output_dir, frame_filename), thumb)
            saved_frame_urls.append(f"frames/{frame_filename}")

    cap.release()

    if frames_analyzed == 0:
        raise ValueError("Could not decode any frames from the uploaded video.")

    # Temporal consistency score (0-100, higher = smoother natural motion)
    if frame_diffs:
        diff_std = float(np.std(frame_diffs))
        temporal_score = round(max(15.0, min(99.5, 96.0 - diff_std * 2.2)), 2)
    else:
        temporal_score = 88.0

    # Artifact / spectral anomaly score (0-100, lower = cleaner, higher = more artifacts)
    mean_hf = float(np.mean(hf_scores)) if hf_scores else 0.05
    mean_lap = float(np.mean(lap_scores)) if lap_scores else 120.0
    lap_std = float(np.std(lap_scores)) if len(lap_scores) > 1 else 10.0

    # Over-smoothed faces (low laplacian) or abrupt sharpness jumps suggest synthesis
    smoothness_penalty = max(0.0, (90.0 - min(mean_lap, 90.0)) / 90.0) * 38.0
    jitter_penalty = min(35.0, lap_std / 8.0)
    hf_penalty = min(27.0, mean_hf * 260.0)
    artifact_score = round(min(98.0, max(4.0, smoothness_penalty + jitter_penalty + hf_penalty)), 2)

    if model_fake_probs:
        fake_probability = float(np.mean(model_fake_probs))
    else:
        # Combine forensic signals into a calibrated probability
        combined_risk = (artifact_score * 0.65 + (100.0 - temporal_score) * 0.35) / 100.0
        fake_probability = float(min(0.99, max(0.01, combined_risk)))

    if fake_probability >= 0.50:
        predicted_class = "FAKE"
        confidence = round(fake_probability * 100.0, 4)
    else:
        predicted_class = "REAL"
        confidence = round((1.0 - fake_probability) * 100.0, 4)

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "frames_analyzed": frames_analyzed,
        "faces_detected": faces_detected,
        "temporal_score": temporal_score,
        "artifact_score": artifact_score,
        "duration_seconds": duration_seconds,
        "sample_frames": saved_frame_urls,
    }
