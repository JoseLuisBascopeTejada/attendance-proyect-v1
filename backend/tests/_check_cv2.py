import cv2
import os

print("cv2 version:", cv2.__version__)
print("cv2 path:", cv2.__file__)
opencv_path = os.path.dirname(cv2.__file__)
data_dir = os.path.join(opencv_path, "data")
print("data dir exists:", os.path.exists(data_dir))
if os.path.exists(data_dir):
    print("data dir contents:", os.listdir(data_dir))
else:
    print("data dir MISSING")
    # Check if cascade files are elsewhere
    for root, dirs, files in os.walk(opencv_path):
        for f in files:
            if "haarcascade" in f:
                print("Found:", os.path.join(root, f))
