---
name: byox-visual-recognition
description: Build image recognition: CNN, transfer learning, face detection, OCR
---
GOAL: a classifier that reaches 95%+ on a dataset without a pre-trained backbone.

PHASES
1. Load dataset (CIFAR-10), normalise; train 3-layer CNN with Adam.
2. Confusion matrix, precision, recall, F1; identify the worst-performing class.
3. Transfer learning: replace final layer of MobileNetV2; fine-tune on custom data.
4. Object detection: YOLOv8 inference on a webcam frame; draw bounding boxes.
5. OCR pipeline: threshold → contours → Tesseract; post-process with language model.

CORE CONCEPTS
- Conv layer: each filter = (kH×kW×C_in) weights; output = sum of dot products + bias.
- Transfer learning: freeze backbone; only train the new head for first 5 epochs.
- im2col: reshape input to a matrix so conv becomes a single GEMM call.

VERIFY: 95%+ accuracy on CIFAR-10 test set; webcam object detection runs at 10+ fps.
