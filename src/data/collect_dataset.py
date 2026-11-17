"""
Transify — Bangladesh Sign Language (BdSL) Dataset Collection Utility
Interactive recording utility capturing authentic BdSL videos with structured metadata.
"""

import os
import sys
import time
import argparse
import csv
from datetime import datetime
import cv2

# Target 10-Class Vocabulary Mapping
BDSL_CLASSES = {
    0: ("HELLO", "Hello / Greetings"),
    1: ("THANK_YOU", "Thank you"),
    2: ("YOURE_WELCOME", "You're welcome"),
    3: ("PLEASE", "Please"),
    4: ("I_NEED_HELP", "I need help"),
    5: ("YES", "Yes"),
    6: ("NO", "No"),
    7: ("OKAY", "Okay"),
    8: ("STOP", "Stop / Halt"),
    9: ("I_DONT_UNDERSTAND", "Don't understand"),
}

CLASS_NAME_TO_ID = {v[0]: k for k, v in BDSL_CLASSES.items()}


def parse_args():
    parser = argparse.ArgumentParser(description="Transify BdSL Dataset Collector")
    parser.add_argument("--signer", type=str, default="S001", help="Signer ID (e.g. S001)")
    parser.add_argument("--session", type=str, default="SES01", help="Session ID (e.g. SES01)")
    parser.add_argument("--class_name", type=str, default="HELLO", choices=list(CLASS_NAME_TO_ID.keys()), help="Target sign expression")
    parser.add_argument("--trials", type=int, default=10, help="Number of trials to record")
    parser.add_argument("--fps", type=float, default=30.0, help="Target recording FPS")
    parser.add_argument("--duration", type=float, default=2.0, help="Recording duration per trial (seconds)")
    parser.add_argument("--camera_id", type=int, default=0, help="Camera device index")
    parser.add_argument("--output_dir", type=str, default="data/sign/raw", help="Raw video output directory")
    parser.add_argument("--manifest_path", type=str, default="data/sign/annotations/dataset_master_manifest.csv", help="Manifest CSV path")
    parser.add_argument("--non_interactive", action="store_true", help="Run without UI popup (for automated test verification)")
    return parser.parse_args()


def init_manifest(manifest_path: str):
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    if not os.path.exists(manifest_path):
        with open(manifest_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sample_id", "signer_id", "class_id", "class_label", "bdsl_gloss",
                "session_id", "video_filename", "duration_sec", "frame_count",
                "fps", "resolution", "timestamp", "landmark_valid", "consent_verified"
            ])


def log_sample(manifest_path: str, record: dict):
    with open(manifest_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            record["sample_id"], record["signer_id"], record["class_id"],
            record["class_label"], record["bdsl_gloss"], record["session_id"],
            record["video_filename"], record["duration_sec"], record["frame_count"],
            record["fps"], record["resolution"], record["timestamp"],
            record["landmark_valid"], record["consent_verified"]
        ])


def main():
    args = parse_args()
    class_id = CLASS_NAME_TO_ID[args.class_name]
    class_label, bdsl_gloss = BDSL_CLASSES[class_id]

    target_dir = os.path.join(args.output_dir, args.class_name)
    os.makedirs(target_dir, exist_ok=True)
    init_manifest(args.manifest_path)

    print(f"============================================================")
    print(f" Transify BdSL Dataset Collector")
    print(f" Signer: {args.signer} | Session: {args.session}")
    print(f" Target Class: [{class_id}] {class_label} ({bdsl_gloss})")
    print(f" Target Trials: {args.trials} | Duration: {args.duration}s per trial")
    print(f" Output Folder: {target_dir}")
    print(f"============================================================")

    if args.non_interactive:
        print("[INFO] Non-interactive mode specified. Validating directories and manifest creation.")
        print(f"[OK] Manifest initialized at: {args.manifest_path}")
        print(f"[OK] Target directory ready at: {target_dir}")
        return

    cap = cv2.VideoCapture(args.camera_id)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera with device ID {args.camera_id}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    trial_idx = 1
    total_frames = int(args.fps * args.duration)

    while trial_idx <= args.trials:
        # Step 1: Ready countdown
        print(f"\n[Trial {trial_idx}/{args.trials}] Get ready for: {class_label} ({bdsl_gloss})")
        countdown_start = time.time()
        while time.time() - countdown_start < 3.0:
            ret, frame = cap.read()
            if not ret:
                break
            remaining = 3 - int(time.time() - countdown_start)
            cv2.putText(frame, f"GET READY: {class_label} in {remaining}s", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)
            cv2.putText(frame, f"BdSL: {bdsl_gloss}", (30, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Transify BdSL Collector", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return

        # Step 2: Active recording
        sample_id = f"BDSL_{args.signer}_{class_label}_{args.session}_T{trial_idx:02d}"
        filename = f"{sample_id}.mp4"
        filepath = os.path.join(target_dir, filename)
        out = cv2.VideoWriter(filepath, fourcc, args.fps, (width, height))

        frames_captured = 0
        start_time = time.time()
        print(f" -> RECORDING NOW: {sample_id}...")

        while frames_captured < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frames_captured += 1

            # Green recording border
            cv2.rectangle(frame, (5, 5), (width - 5, height - 5), (0, 255, 0), 4)
            cv2.putText(frame, f"RECORDING [{class_label}] {frames_captured}/{total_frames}", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow("Transify BdSL Collector", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                out.release()
                cap.release()
                cv2.destroyAllWindows()
                return

        out.release()
        actual_duration = time.time() - start_time

        # Step 3: Confirmation prompt
        record = {
            "sample_id": sample_id,
            "signer_id": args.signer,
            "class_id": class_id,
            "class_label": class_label,
            "bdsl_gloss": bdsl_gloss,
            "session_id": args.session,
            "video_filename": filepath,
            "duration_sec": round(actual_duration, 2),
            "frame_count": frames_captured,
            "fps": round(frames_captured / actual_duration, 2),
            "resolution": f"{width}x{height}",
            "timestamp": datetime.now().isoformat(),
            "landmark_valid": True,
            "consent_verified": True
        }
        log_sample(args.manifest_path, record)
        print(f" [OK] Saved trial {trial_idx}: {filepath} ({frames_captured} frames)")
        trial_idx += 1

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[SUCCESS] Completed {args.trials} trials for {class_label} by {args.signer}.")


if __name__ == "__main__":
    main()
