"""
Transify — Dataset Inspection and Integrity Verification Utility
Scans the dataset directory, validates video streams, detects corrupted files, and audits class balance.
"""

import os
import glob
import json
import argparse
import cv2
import pandas as pd

BDSL_EXPECTED_CLASSES = [
    "HELLO", "THANK_YOU", "YOURE_WELCOME", "PLEASE", "I_NEED_HELP",
    "YES", "NO", "OKAY", "STOP", "I_DONT_UNDERSTAND"
]


def parse_args():
    parser = argparse.ArgumentParser(description="Transify Dataset Inspector")
    parser.add_argument("--data_dir", type=str, default="data/sign/raw", help="Path to raw video root")
    parser.add_argument("--manifest_path", type=str, default="data/sign/annotations/dataset_master_manifest.csv", help="Manifest CSV")
    parser.add_argument("--report_out", type=str, default="data/sign/annotations/dataset_quality_audit.json", help="Output audit report JSON")
    return parser.parse_args()


def inspect_videos(data_dir: str):
    audit_results = {
        "total_files_scanned": 0,
        "valid_videos": 0,
        "corrupted_videos": 0,
        "classes_found": {},
        "signers_found": set(),
        "corrupted_file_list": [],
        "durations_sec": [],
        "frame_counts": [],
        "resolutions": set(),
    }

    for class_name in BDSL_EXPECTED_CLASSES:
        class_folder = os.path.join(data_dir, class_name)
        if not os.path.exists(class_folder):
            audit_results["classes_found"][class_name] = 0
            continue

        video_files = glob.glob(os.path.join(class_folder, "*.mp4")) + glob.glob(os.path.join(class_folder, "*.avi"))
        audit_results["classes_found"][class_name] = len(video_files)
        audit_results["total_files_scanned"] += len(video_files)

        for vf in video_files:
            cap = cv2.VideoCapture(vf)
            if not cap.isOpened():
                audit_results["corrupted_videos"] += 1
                audit_results["corrupted_file_list"].append({"file": vf, "reason": "Failed to open with cv2"})
                continue

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if frame_count <= 0 or fps <= 0:
                audit_results["corrupted_videos"] += 1
                audit_results["corrupted_file_list"].append({"file": vf, "reason": f"Zero frames ({frame_count}) or FPS ({fps})"})
                continue

            audit_results["valid_videos"] += 1
            duration = frame_count / fps
            audit_results["durations_sec"].append(duration)
            audit_results["frame_counts"].append(frame_count)
            audit_results["resolutions"].add(f"{w}x{h}")

            # Parse signer ID from filename
            base = os.path.basename(vf)
            parts = base.split("_")
            if len(parts) >= 2 and parts[0] == "BDSL":
                audit_results["signers_found"].add(parts[1])

    audit_results["signers_found"] = list(audit_results["signers_found"])
    audit_results["resolutions"] = list(audit_results["resolutions"])
    if audit_results["durations_sec"]:
        audit_results["mean_duration_sec"] = sum(audit_results["durations_sec"]) / len(audit_results["durations_sec"])
        audit_results["min_duration_sec"] = min(audit_results["durations_sec"])
        audit_results["max_duration_sec"] = max(audit_results["durations_sec"])
    else:
        audit_results["mean_duration_sec"] = 0.0
        audit_results["min_duration_sec"] = 0.0
        audit_results["max_duration_sec"] = 0.0

    # Cleanup large list before export
    audit_results.pop("durations_sec", None)
    audit_results.pop("frame_counts", None)

    return audit_results


def main():
    args = parse_args()
    print("=" * 60)
    print(" Transify Dataset Quality Inspection")
    print(f" Scanning directory: {args.data_dir}")
    print("=" * 60)

    results = inspect_videos(args.data_dir)

    print(f"\n[SUMMARY]")
    print(f"Total Video Files Scanned: {results['total_files_scanned']}")
    print(f"Valid Video Files:         {results['valid_videos']}")
    print(f"Corrupted Files Detected:  {results['corrupted_videos']}")
    print(f"Signers Identified:        {len(results['signers_found'])} {results['signers_found']}")
    print(f"Resolutions Detected:      {results['resolutions']}")
    print(f"Duration Range:            {results['min_duration_sec']:.2f}s - {results['max_duration_sec']:.2f}s (Mean: {results['mean_duration_sec']:.2f}s)")

    print(f"\n[CLASS DISTRIBUTION]")
    for c in BDSL_EXPECTED_CLASSES:
        count = results["classes_found"].get(c, 0)
        status = "OK" if count >= 20 else ("PARTIAL" if count > 0 else "EMPTY")
        print(f"  - {c:<20}: {count:>4} samples [{status}]")

    os.makedirs(os.path.dirname(args.report_out), exist_ok=True)
    with open(args.report_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Quality audit report saved to: {args.report_out}")


if __name__ == "__main__":
    main()
