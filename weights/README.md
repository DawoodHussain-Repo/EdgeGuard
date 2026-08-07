# EdgeGuard-AI Model Weights & Detection Modes

EdgeGuard-AI supports two high-performance computer vision model options: **Zero-Shot YOLO-World** (zero pre-downloads required) and **Custom Fine-Tuned YOLO Weights**.

---

## Option 1: YOLO-World (Built-In Zero-Shot Open-Vocabulary)

No custom model downloads are required! EdgeGuard-AI automatically initializes **YOLO-World** (`yolov8s-worldv2.pt`) built into the `ultralytics` package.

YOLO-World allows dynamically passing custom text prompts for safety inspection:

```python
from ultralytics import YOLOWorld

# Automatically downloads model on first run
model = YOLOWorld("yolov8s-worldv2.pt")

# Set exact classes for worker safety monitoring
model.set_classes(["person", "hardhat", "safety vest", "no helmet", "no safety vest"])

# Run ByteTrack multi-object tracking
results = model.track(source="video.mp4", tracker="bytetrack.yaml")
```

---

## Option 2: Custom Fine-Tuned Model Weights (`weights/ppe_yolov8n.pt`)

If you prefer using a domain-specific model fine-tuned on custom construction site datasets, place your `.pt` file here as `weights/ppe_yolov8n.pt`.

### Where to Get Custom PPE Model Weights:

1. **Roboflow Universe (Recommended)**:
   - Search for **"Construction Site Safety"** or **"PPE Detection"** on [Roboflow Universe](https://universe.roboflow.com/).
   - Popular pre-annotated datasets include:
     - `hard-hat-workers`
     - `construction-site-safety-dataset`
   - Download the model weights directly in **YOLOv8 PyTorch format** (`.pt`).

2. **Kaggle Datasets**:
   - Search for **"Worker Safety PPE Detection YOLOv8"** on Kaggle.

3. **Train Your Own Model**:
   - Train a custom model using Ultralytics CLI:
     ```bash
     yolo detect train data=ppe_dataset.yaml model=yolov8n.pt epochs=50 imgsz=640
     ```
   - Copy the trained `runs/detect/train/weights/best.pt` to `weights/ppe_yolov8n.pt`.

---

## Model Fallback Priority Hierarchy

EdgeGuard-AI automatically selects the optimal detection engine in the following order:

1. **Custom Model**: `weights/ppe_yolov8n.pt` (if file exists in `weights/`).
2. **YOLO-World**: `yolov8s-worldv2.pt` (zero-shot text-prompt open-vocabulary detection).
3. **Adaptive Synthetic Mode**: High-framerate simulated pipeline (runs if offline or without model files).
