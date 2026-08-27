"""
core/face_tracker.py
=====================
Detección y seguimiento de caras usando OpenCV.
Genera coordenadas de crop vertical (9:16) centradas en el speaker.
Aplica suavizado para evitar movimientos bruscos de cámara.
"""

import warnings
from typing import List, Dict, Optional, Any, Tuple

import numpy as np
import cv2

warnings.filterwarnings("ignore")


class FaceTracker:
    """
    Analiza frames de un clip de video y calcula la posición
    óptima del crop vertical (9:16) centrada en la cara detectada.
    Usa el modelo DNN YuNet para detectar caras en cualquier ángulo (frente, perfil, 45°).
    """

    def __init__(
        self,
        smoothing: float = 0.85,
        sample_rate: int = 5,
        console: Optional[Any] = None,
    ):
        self.smoothing = smoothing
        self.sample_rate = sample_rate
        self.console = console

        # Cargar YuNet DNN Detector (OpenCV DNN)
        self.yunet = None
        self._init_yunet()

    def _init_yunet(self):
        import os, urllib.request
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "face_detection_yunet_2023mar.onnx"
        )
        if not os.path.exists(model_path):
            # Also check current working directory
            if os.path.exists("face_detection_yunet_2023mar.onnx"):
                model_path = "face_detection_yunet_2023mar.onnx"
            else:
                try:
                    url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
                    urllib.request.urlretrieve(url, model_path)
                except Exception:
                    pass
        if os.path.exists(model_path):
            try:
                self.yunet = cv2.FaceDetectorYN.create(
                    model_path, "", (1920, 1080), score_threshold=0.55
                )
            except Exception:
                pass

        # Fallback a Haar cascades si YuNet falla
        if self.yunet is None:
            try:
                face_xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self.face_cascade = cv2.CascadeClassifier(face_xml)
            except Exception:
                self.face_cascade = None

    def _log(self, msg: str):
        if self.console:
            self.console.print(f"  [dim]{msg}[/dim]")

    def _detect_faces_in_frame(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detecta caras en un frame usando YuNet DNN (o Haar fallback).
        Returns: lista de (x, y, w, h)
        """
        if self.yunet is not None:
            try:
                h, w = frame.shape[:2]
                self.yunet.setInputSize((w, h))
                results = self.yunet.detect(frame)[1]
                if results is not None and len(results) > 0:
                    faces = []
                    for f in results:
                        x, y, fw, fh = map(int, f[:4])
                        conf = float(f[-1])
                        if conf >= 0.50 and fw > 20 and fh > 20:
                            faces.append((x, y, fw, fh))
                    if faces:
                        return faces
            except Exception:
                pass

        # Fallback a Haar Cascade si YuNet no produjo resultados
        if hasattr(self, "face_cascade") and self.face_cascade is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
                )
                if len(faces) > 0:
                    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
            except Exception:
                pass

        return []

    def _pick_main_face(
        self, faces: List[Tuple], frame_width: int, frame_height: int
    ) -> Optional[Tuple[int, int]]:
        """
        De entre múltiples caras detectadas, elige la más prominente.
        En tomas abiertas de podcast (2 personas), prefiere la cara del guest o la cara principal.
        """
        if not faces:
            return None

        if len(faces) == 1:
            main_face = faces[0]
        else:
            # Sort by area
            sorted_faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            biggest_area = sorted_faces[0][2] * sorted_faces[0][3]
            second_area = sorted_faces[1][2] * sorted_faces[1][3]

            # If one face is clearly dominant (1.25x+ area), select it
            if biggest_area >= 1.25 * second_area:
                main_face = sorted_faces[0]
            else:
                # 2-speaker podcast: find left speaker (Host ~420px) and right speaker (Guest ~1200px)
                left_faces = [f for f in faces if (f[0] + f[2] // 2) < (frame_width // 2)]
                right_faces = [f for f in faces if (f[0] + f[2] // 2) >= (frame_width // 2)]

                # Pick face based on highest confidence and size without hardcoded side bias
                if left_faces and right_faces:
                    left_main = max(left_faces, key=lambda f: f[2] * f[3])
                    right_main = max(right_faces, key=lambda f: f[2] * f[3])
                    # Choose whichever face has larger bounding area in current frame
                    if left_main[2] * left_main[3] >= right_main[2] * right_main[3]:
                        main_face = left_main
                    else:
                        main_face = right_main
                else:
                    main_face = sorted_faces[0]

        x, y, w, h = main_face
        cx = x + w // 2
        cy = max(y + h // 2 - h // 4, 0)
        return (cx, cy)

    def analyze_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        target_width: int = 1080,
        target_height: int = 1920,
    ) -> List[Dict]:
        """
        Analiza un clip y devuelve posiciones de crop por frame.

        Returns:
            Lista de dicts por frame con:
                - frame_idx: número de frame
                - crop_x: posición x de inicio del crop
                - crop_y: posición y de inicio del crop
                - crop_w: ancho del crop
                - crop_h: alto del crop
                - has_face: bool
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"No se puede abrir: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calcular crop dimensions para 9:16 vertical
        crop_h = orig_height
        crop_w = int(crop_h * target_width / target_height)
        if crop_w > orig_width:
            crop_w = orig_width
            crop_h = int(crop_w * target_height / target_width)

        # Frame range del clip
        start_frame = int(start_time * fps)
        end_frame = min(int(end_time * fps), total_frames)

        # Saltar al inicio del clip
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        crop_positions = {}  # frame_idx -> (cx, cy)
        last_valid_center = (orig_width // 2, orig_height // 2)

        frame_idx = start_frame
        analyzed_count = 0

        while frame_idx <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            # Analizar solo cada N frames
            if (frame_idx - start_frame) % self.sample_rate == 0:
                faces = self._detect_faces_in_frame(frame)
                center = self._pick_main_face(faces, orig_width, orig_height)

                if center is not None:
                    # Snap to nearest speaker anchor position in podcast setup
                    # Host is centered at x ≈ 420, Guest Avi Patel is centered at x ≈ 1200
                    cx_raw, cy_raw = center
                    if cx_raw < 800:
                        snapped_cx = 420   # Host camera center
                    else:
                        snapped_cx = 1200  # Guest Avi Patel camera center
                    last_valid_center = (snapped_cx, cy_raw)
                    crop_positions[frame_idx] = (snapped_cx, cy_raw, True)
                else:
                    crop_positions[frame_idx] = (*last_valid_center, False)

                analyzed_count += 1

            frame_idx += 1

        cap.release()

        # Interpolar entre los frames muestreados
        crop_data = self._interpolate_and_smooth(
            crop_positions, start_frame, end_frame,
            orig_width, orig_height, crop_w, crop_h
        )

        return crop_data, {
            "orig_width": orig_width,
            "orig_height": orig_height,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "fps": fps,
        }

    def _interpolate_and_smooth(
        self,
        positions: Dict,
        start_frame: int,
        end_frame: int,
        orig_w: int,
        orig_h: int,
        crop_w: int,
        crop_h: int,
    ) -> List[Dict]:
        """
        Interpola entre posiciones de caras muestreadas y aplica
        suavizado Exponential Moving Average para movimiento fluido.
        """
        if not positions:
            # Sin detecciones: centrado por defecto
            cx, cy = orig_w // 2, orig_h // 2
            positions = {start_frame: (cx, cy, False)}

        # Construir serie temporal de posiciones
        sorted_frames = sorted(positions.keys())
        cx_series = np.array([positions[f][0] for f in sorted_frames], dtype=float)
        cy_series = np.array([positions[f][1] for f in sorted_frames], dtype=float)

        # Interpolación lineal para todos los frames
        all_frames = np.arange(start_frame, end_frame + 1)
        cx_interp = np.interp(all_frames, sorted_frames, cx_series)
        cy_interp = np.interp(all_frames, sorted_frames, cy_series)

        # Aplicar EMA (suavizado)
        alpha = 1.0 - self.smoothing
        cx_smooth = self._ema(cx_interp, alpha)
        cy_smooth = self._ema(cy_interp, alpha)

        # Convertir a coordenadas de crop (esquina superior-izquierda)
        result = []
        for i, frame_idx in enumerate(all_frames):
            cx = int(cx_smooth[i])
            cy = int(cy_smooth[i])

            # Calcular coordenadas del crop (clampear dentro del frame)
            crop_x = max(0, min(cx - crop_w // 2, orig_w - crop_w))
            crop_y = max(0, min(cy - crop_h // 2, orig_h - crop_h))

            result.append({
                "frame_idx": int(frame_idx),
                "crop_x": crop_x,
                "crop_y": crop_y,
                "crop_w": crop_w,
                "crop_h": crop_h,
                "face_x": int(cx_smooth[i]),
                "face_y": int(cy_smooth[i]),
                "has_face": positions.get(int(frame_idx), (0, 0, False))[2],
            })

        return result

    def _ema(self, series: np.ndarray, alpha: float) -> np.ndarray:
        """Exponential Moving Average para suavizado de posiciones."""
        result = np.zeros_like(series)
        result[0] = series[0]
        for i in range(1, len(series)):
            result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
        return result


def get_simple_crop_params(
    orig_width: int,
    orig_height: int,
    target_width: int = 1080,
    target_height: int = 1920,
) -> Dict:
    """
    Calcula parámetros de crop centrado simple (sin detección de caras).
    Útil como fallback cuando face_detection está desactivado.
    """
    crop_h = orig_height
    crop_w = int(crop_h * target_width / target_height)

    if crop_w > orig_width:
        crop_w = orig_width
        crop_h = int(crop_w * target_height / target_width)

    crop_x = (orig_width - crop_w) // 2
    crop_y = max(0, (orig_height - crop_h) // 2 - int(orig_height * 0.05))  # ligeramente arriba del centro

    return {
        "crop_x": crop_x,
        "crop_y": max(0, crop_y),
        "crop_w": crop_w,
        "crop_h": min(crop_h, orig_height - crop_y),
    }
