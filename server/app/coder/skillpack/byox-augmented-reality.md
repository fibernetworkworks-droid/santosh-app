---
name: byox-augmented-reality
description: Build an AR app with ArUco marker tracking and 3D overlay
---
GOAL: a live camera feed with a 3D cube rendered correctly on top of a printed marker.

PHASES
1. Calibrate camera: checkerboard + cv2.calibrateCamera; save intrinsic matrix.
2. Detect ArUco markers in each frame; get 4 corner points.
3. solvePnP: compute rvec + tvec; project 3D cube corners to 2D pixels.
4. Draw cube edges with cv2.drawContours; occlusion via depth buffer.
5. Port to mobile with ARCore / ARKit or Unity ARFoundation.

CORE CONCEPTS
- Camera matrix K = [[fx,0,cx],[0,fy,cy],[0,0,1]]; distortion coeffs d.
- Rodrigues: rotation vector → 3×3 rotation matrix for OpenGL.

VERIFY: cube stays locked to the marker even as the camera moves; no drift.
