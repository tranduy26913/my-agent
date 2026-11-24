"""Phân tách người nói bằng sherpa-onnx (pyannote segmentation + embedding 3D-Speaker, ONNX, chạy CPU, không cần token).

Không biết trước số người và tên: gom theo độ giống giọng. Model nằm ở DIAR_DIR (mặc định models/diarization/):
    segmentation.onnx   (sherpa-onnx-pyannote-segmentation-3-0/model.onnx)
    embedding.onnx      (3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx)
Thiếu file hoặc thiếu gói sherpa-onnx thì `available()` là False và server chép lời không có nhãn người nói.
"""

import os
import threading

import numpy as np

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAR_DIR = os.environ.get("STT_DIAR_DIR") or os.path.join(_BASE, "models", "diarization")
THRESHOLD = float(os.environ.get("STT_DIAR_THRESHOLD", "0.7"))  # cao hơn = ít người hơn (gộp dễ hơn). Đo trên 2 giọng: 0.5 ra 6 người, 0.7-0.9 ra đúng 2
THREADS = int(os.environ.get("STT_DIAR_THREADS", "4"))
_SEG = os.path.join(DIAR_DIR, "segmentation.onnx")
_EMB = os.path.join(DIAR_DIR, "embedding.onnx")

_lock = threading.Lock()


def available() -> bool:
    if not (os.path.isfile(_SEG) and os.path.isfile(_EMB)):
        return False
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return False
    return True


def diarize(audio: np.ndarray, *, num_speakers: int | None = None) -> list[tuple[float, float, int]]:
    """audio: float32 mono 16 kHz. Trả [(start, end, speaker_id)] theo thời gian; speaker_id đánh số theo clustering."""
    import sherpa_onnx

    with _lock:
        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=_SEG), num_threads=THREADS
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=_EMB, num_threads=THREADS),
            clustering=sherpa_onnx.FastClusteringConfig(num_clusters=num_speakers or -1, threshold=THRESHOLD),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        sd = sherpa_onnx.OfflineSpeakerDiarization(config)
        if sd.sample_rate != 16000:
            raise RuntimeError(f"model phân tách người nói cần {sd.sample_rate} Hz, server chỉ đưa 16000 Hz")
        result = sd.process(audio).sort_by_start_time()
        return [(float(r.start), float(r.end), int(r.speaker)) for r in result]
