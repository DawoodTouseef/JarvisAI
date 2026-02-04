"""YOLO object detection integration (Ultralytics)."""

from __future__ import annotations

import os
from typing import Any, Dict, List


class YoloDetector:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or os.getenv("YOLO_MODEL_PATH") or os.path.join("server", "yolov8n-pose.pt")
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise RuntimeError("Ultralytics is not installed. Install 'ultralytics' to enable YOLO.") from exc
        self._model = YOLO(self.model_path)
        return self._model

    def detect(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        model = self._load_model()
        results = model.predict(source=image_bytes, imgsz=640, conf=0.25, verbose=False)
        detections: List[Dict[str, Any]] = []
        for result in results:
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0]) if hasattr(box, "cls") else None
                conf = float(box.conf[0]) if hasattr(box, "conf") else None
                xyxy = box.xyxy[0].tolist() if hasattr(box, "xyxy") else None
                detections.append(
                    {
                        "class_id": cls_id,
                        "class_name": names.get(cls_id) if isinstance(names, dict) and cls_id is not None else None,
                        "confidence": conf,
                        "bbox_xyxy": xyxy,
                    }
                )
        return detections
