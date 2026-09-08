import os
import sys
import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

video_path = os.path.abspath(r"output/test_semantic_long.mp4")
if not os.path.exists(video_path):
    print(f"Error: {video_path} does not exist!")
    sys.exit(1)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
dur = total_frames / fps if fps > 0 else 0

print(f"=== VIDEO VERIFICATION: {os.path.basename(video_path)} ===")
print(f"Resolution: {w}x{h}")
print(f"FPS: {fps:.2f}")
print(f"Total Frames: {total_frames}")
print(f"Total Duration: {dur:.2f}s")

# Sample across video to check black frames and brightness
black_frames = 0
min_bright = 255.0
max_bright = 0.0
sample_step = max(1, int(fps / 2))  # check 2 times per second

sampled_timestamps = []
f_idx = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    if f_idx % sample_step == 0:
        t = f_idx / fps
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_b = float(np.mean(gray))
        min_bright = min(min_bright, mean_b)
        max_bright = max(max_bright, mean_b)
        if mean_b < 2.0:
            black_frames += 1
            print(f"⚠️ Black frame detected at {t:.2f}s (mean brightness: {mean_b:.2f})")
        sampled_timestamps.append((t, mean_b))
    f_idx += 1

cap.release()

print(f"\n--- Results across {len(sampled_timestamps)} sampled timestamps ---")
print(f"Black frames detected: {black_frames} (0 expected)")
print(f"Brightness range: {min_bright:.2f} min - {max_bright:.2f} max")

# Save keyframe previews at specific event timestamps to artifact storage
sample_times = [1.0, 7.5, 9.5, 20.5, 25.5, 30.5]
cap = cv2.VideoCapture(video_path)
for st in sample_times:
    f_num = int(st * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        out_prev = os.path.abspath(f"output/preview_frame_{int(st)}s.jpg")
        cv2.imwrite(out_prev, frame)
        print(f"Saved preview frame at {st}s: {out_prev}")
cap.release()

print("\n✓ Video verification completed successfully!")
