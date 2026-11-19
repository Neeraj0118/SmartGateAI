# Third-Party Licenses & Model Attributions

This project uses pre-trained computer vision models from the official OpenCV Zoo.
The licensing terms, origin, and technical specifications for each model are recorded below.

---

## 1. Face Detection Model: YuNet
* **Model File**: `face_detection_yunet_2023mar.onnx`
* **Architecture**: YuNet (Sample and Computation Redistribution for Efficient Face Detection)
* **Author / Project**: Shiqi Yu et al., Shenzhen Key Laboratory of Media Surveillance, OpenCV Foundation
* **Repository**: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
* **License**: **Apache License 2.0**
* **License Reference**: Distributed in the OpenCV Zoo repository under `models/face_detection_yunet/LICENSE`
* **Commercial Use**: Permitted under Apache 2.0 terms.
* **Input**: BGR image of arbitrary resolution $(H, W, 3)$
* **Output**: Array of detected faces, each containing:
  - Bounding box: $[x, y, w, h]$
  - 5 facial landmarks: right eye, left eye, nose tip, right mouth corner, left mouth corner
  - Confidence score: $[0.0, 1.0]$

---

## 2. Face Recognition Model: SFace
* **Model File**: `face_recognition_sface_2021dec.onnx`
* **Architecture**: SFace (Sigmoid-Constrained Hypersphere Loss for Robust Face Recognition)
* **Paper**: Zhong et al., "SFace: Sigmoid-Constrained Hypersphere Loss for Robust Face Recognition", *IEEE Transactions on Image Processing*, 2021.
* **Author / Project**: OpenCV Foundation / SFace Authors
* **Repository**: https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
* **License**: **Apache License 2.0**
* **License Reference**: Distributed in the OpenCV Zoo repository under `models/face_recognition_sface/LICENSE`
* **Commercial Use**: Permitted under Apache 2.0 terms.
* **Input**: $112 \times 112$ canonical aligned RGB face crop
* **Output Embedding Dimension**: **128-dimensional float32 vector** ($1 \times 128$)
* **Cosine Similarity Threshold**:
  - Distance threshold: $0.363$ ($1 - \text{cosine similarity}$)
  - Equivalent Cosine Similarity threshold: $\ge 0.637$ (configurable: $0.60 - 0.70$ recommended)
