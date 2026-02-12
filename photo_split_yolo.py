from ultralytics import YOLO
import cv2
import os
from pathlib import Path
from tqdm import tqdm

# --- CONFIGURATION ---
MODE = 'predict'  # 'train' or 'predict'

# Paths
# 1. Where the trained model is (or will be saved)
MODEL_PATH = 'runs/detect/train3/weights/best.pt'

# 2. Where your RAW images are (that you want to crop)
# Ensure this folder contains ONLY the images you want to process, not the training folder.
INPUT_FOLDER = 'DHM/DHM_images'

# 3. Where to save results
OUTPUT_FOLDER = 'DHM/DHM_images_split_yolo'

# 4. Where your training config is (Keep this OUTSIDE the input_images folder)
TRAINING_YAML = 'DHM/test/input/training_yolo/data.yaml'


# ---------------------

def train_model():
    """
    Trains a YOLOv8 model.
    """
    print(f"Starting training using config: {TRAINING_YAML}")

    # Load a pre-trained model
    model = YOLO('yolov8n.pt')

    # Train
    # We specify the project/name so we know exactly where it saves,
    # but defaults (runs/detect/train) are fine too.

    # results = model.train(data=TRAINING_YAML, epochs=50, imgsz=640, device="cpu")
    results = model.train(data=TRAINING_YAML, epochs=50, imgsz=640)  # use device="cpu" for  training"

    print(f"Training complete! Model saved to {MODEL_PATH}")


def process_images_with_ai():
    """
    Uses the trained model to find photos and crop them.
    """
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}. Please train it first.")
        return

    model = YOLO(MODEL_PATH)

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Get a list of images just for the progress bar count
    # YOLO handles the actual loading, but we want to know how many total files there are.
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tif']
    total_files = 0
    input_path = Path(INPUT_FOLDER)
    for ext in image_extensions:
        total_files += len(list(input_path.glob(ext)))

    print(f"Found ~{total_files} images in {INPUT_FOLDER}. Starting inference...")

    # Run inference
    # stream=True returns a python generator (memory efficient)
    results = model.predict(source=INPUT_FOLDER, stream=True, conf=0.5, iou=0.7)

    # Wrap results in tqdm for a progress bar
    for result in tqdm(results, total=total_files, desc="Processing"):

        path = Path(result.path)
        img = result.orig_img

        # If no detections, write original image to output
        if len(result.boxes) == 0:
            save_name = f"{path.stem}.jpg"
            cv2.imwrite(os.path.join(OUTPUT_FOLDER, save_name), img)
            continue

        # Iterate through detected boxes
        for i, box in enumerate(result.boxes):
            try:
                # Get coordinates
                coords = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = coords

                # Safety clamp (ensure we don't crop outside image boundaries)
                h, w, _ = img.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                crop = img[y1:y2, x1:x2]

                # Save
                save_name = f"{path.stem}_{i}.jpg"
                # if len(result.boxes) > 1:
                #     save_name = f"{path.stem}_{i}.jpg"
                # else:
                #     save_name = f"{path.stem}.jpg"

                cv2.imwrite(os.path.join(OUTPUT_FOLDER, save_name), crop)

            except Exception as e:
                print(f"Error saving crop for {path.name}: {e}")


if __name__ == "__main__":
    if MODE == 'train':
        train_model()
    else:
        process_images_with_ai()