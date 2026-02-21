"""Picamera OpenCV 检测模块

提供运动检测、人脸检测功能，支持物体识别和目标跟踪扩展。
所有检测结果以 (原始图片, 标注图片, JSON) 三元组返回。
"""

import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV 未安装，检测功能已禁用。安装方式: pip install opencv-python")


class Detection:
    """单个检测结果（一个边界框）。"""

    def __init__(self, label: str, category: str,
                 x: int, y: int, w: int, h: int,
                 confidence: float = 1.0) -> None:
        self.label = label
        self.category = category  # "motion" | "face" | "object" | "tracking"
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "category": self.category,
            "bbox": {"x": self.x, "y": self.y, "w": self.w, "h": self.h},
            "confidence": round(self.confidence, 3),
        }


class DetectionResult:
    """一帧图片的聚合检测结果。"""

    def __init__(self) -> None:
        self.detections: List[Detection] = []
        self.timestamp: float = time.time()
        self.processing_ms: float = 0.0

    def to_json(self) -> str:
        summary: Dict[str, int] = {}
        for d in self.detections:
            summary[d.category] = summary.get(d.category, 0) + 1

        return json.dumps({
            "timestamp": self.timestamp,
            "processing_ms": round(self.processing_ms, 1),
            "count": len(self.detections),
            "summary": summary,
            "detections": [d.to_dict() for d in self.detections],
        }, ensure_ascii=False)


class Detector:
    """图像检测器，支持运动检测和人脸检测。

    线程安全：process() 内部使用锁序列化处理。
    """

    COLORS = {
        "motion": (0, 255, 0),      # 绿色
        "face": (255, 0, 0),        # 蓝色 (BGR)
        "object": (0, 165, 255),    # 橙色
        "tracking": (255, 255, 0),  # 青色
    }

    def __init__(self, enable_motion: bool = True,
                 enable_face: bool = True,
                 enable_object: bool = False,
                 enable_tracking: bool = False) -> None:
        self._process_lock = threading.Lock()
        self._prev_gray: Optional[Any] = None
        self._enable_motion = enable_motion
        self._enable_face = enable_face
        self._enable_object = enable_object
        self._enable_tracking = enable_tracking
        self._face_cascade = None

        if CV2_AVAILABLE and enable_face:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
            if self._face_cascade.empty():
                logger.warning(f"无法加载人脸级联分类器: {cascade_path}")
                self._face_cascade = None

        features = []
        if enable_motion:
            features.append("运动检测")
        if enable_face:
            features.append("人脸检测")
        if enable_object:
            features.append("物体识别")
        if enable_tracking:
            features.append("目标跟踪")
        logger.info(f"检测器初始化完成，已启用: {', '.join(features) or '无'}")

    def process(self, jpeg_bytes: bytes) -> Tuple[bytes, bytes, str]:
        """处理一帧 JPEG 图片。

        返回: (原始JPEG, 标注JPEG, 检测结果JSON)
        OpenCV 未安装时标注图片等同于原始图片。
        """
        if not CV2_AVAILABLE:
            return (jpeg_bytes, jpeg_bytes, DetectionResult().to_json())

        with self._process_lock:
            return self._process_internal(jpeg_bytes)

    def _process_internal(self, jpeg_bytes: bytes) -> Tuple[bytes, bytes, str]:
        t0 = time.monotonic()

        img_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("JPEG 解码失败")
            return (jpeg_bytes, jpeg_bytes, DetectionResult().to_json())

        result = DetectionResult()
        annotated = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self._enable_motion:
            self._detect_motion(gray, result)
        if self._enable_face:
            self._detect_faces(gray, result)
        if self._enable_object:
            self._detect_objects(frame, result)
        if self._enable_tracking:
            self._track_target(frame, result)

        self._draw_annotations(annotated, result)

        _, annotated_buf = cv2.imencode('.jpg', annotated,
                                        [cv2.IMWRITE_JPEG_QUALITY, 85])
        result.processing_ms = (time.monotonic() - t0) * 1000

        return (jpeg_bytes, annotated_buf.tobytes(), result.to_json())

    def _detect_motion(self, gray: Any, result: DetectionResult) -> None:
        """帧差法运动检测。"""
        if self._prev_gray is None:
            self._prev_gray = gray
            return

        diff = cv2.absdiff(self._prev_gray, gray)
        self._prev_gray = gray

        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        min_area = 500
        for contour in contours:
            if cv2.contourArea(contour) < min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            result.detections.append(
                Detection("运动", "motion", x, y, w, h)
            )

    def _detect_faces(self, gray: Any, result: DetectionResult) -> None:
        """Haar 级联人脸检测。"""
        if self._face_cascade is None:
            return
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        for (x, y, w, h) in faces:
            result.detections.append(
                Detection("人脸", "face", int(x), int(y), int(w), int(h),
                          confidence=0.9)
            )

    def _detect_objects(self, frame: Any, result: DetectionResult) -> None:
        """物体识别（预留接口，需要模型文件）。"""
        pass

    def _track_target(self, frame: Any, result: DetectionResult) -> None:
        """目标跟踪（预留接口）。"""
        pass

    def _draw_annotations(self, frame: Any, result: DetectionResult) -> None:
        """在图片上绘制检测框和标签。"""
        for det in result.detections:
            color = self.COLORS.get(det.category, (255, 255, 255))
            cv2.rectangle(frame,
                          (det.x, det.y),
                          (det.x + det.w, det.y + det.h),
                          color, 2)
            label = det.label
            if det.confidence < 1.0:
                label += f" {det.confidence:.0%}"
            cv2.putText(frame, label,
                        (det.x, det.y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
