# Model Weights Directory

Place custom pre-trained YOLO model weights here.

## Recommended Model File
- `ppe_yolov8n.pt` (Fine-tuned YOLOv8 Nano model on Construction-PPE dataset)

## Supported Classes
- `person` (ID 0)
- `helmet` / `head_gear` / `hard_hat`
- `vest` / `safety_vest` / `high_vis`
- `no_helmet`
- `no_vest`

*Note: If no model file is placed in this directory, EdgeGuard-AI automatically operates in adaptive high-performance synthetic demonstration mode.*
