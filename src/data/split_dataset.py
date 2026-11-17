"""
Transify — Signer-Independent Dataset Splitter
Executes Leave-Signers-Out (LSO) partitioning across the master manifest,
guaranteeing zero signer leakage between train, validation, and test splits.
"""

import os
import argparse
import pandas as pd
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Transify Signer-Independent Dataset Splitter")
    parser.add_argument("--manifest", type=str, default="data/sign/annotations/dataset_master_manifest.csv", help="Master manifest CSV")
    parser.add_argument("--splits_dir", type=str, default="data/sign/splits", help="Output directory for split CSVs")
    parser.add_argument("--train_ratio", type=float, default=0.70, help="Target train signer proportion")
    parser.add_argument("--val_ratio", type=float, default=0.15, help="Target val signer proportion")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def split_dataset(manifest_path: str, splits_dir: str, train_ratio: float = 0.70, val_ratio: float = 0.15, seed: int = 42):
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    df = pd.read_csv(manifest_path)
    if len(df) == 0:
        raise ValueError("Manifest file is empty.")

    signers = sorted(df["signer_id"].unique().tolist())
    n_signers = len(signers)
    print(f"[INFO] Discovered {n_signers} unique signers: {signers}")

    rng = np.random.default_rng(seed)
    shuffled_signers = rng.permutation(signers).tolist()

    # Calculate partition counts
    n_val = max(1, int(round(n_signers * val_ratio)))
    n_test = max(1, int(round(n_signers * (1.0 - train_ratio - val_ratio))))
    n_train = n_signers - n_val - n_test

    if n_train <= 0:
        n_train = n_signers - 2
        n_val = 1
        n_test = 1

    train_signers = shuffled_signers[:n_train]
    val_signers = shuffled_signers[n_train:n_train + n_val]
    test_signers = shuffled_signers[n_train + n_val:]

    # Assert mutual exclusivity (Zero Signer Leakage)
    assert set(train_signers).isdisjoint(set(val_signers)), "Leakage between train and val signers!"
    assert set(train_signers).isdisjoint(set(test_signers)), "Leakage between train and test signers!"
    assert set(val_signers).isdisjoint(set(test_signers)), "Leakage between val and test signers!"

    train_df = df[df["signer_id"].isin(train_signers)].copy()
    val_df = df[df["signer_id"].isin(val_signers)].copy()
    test_df = df[df["signer_id"].isin(test_signers)].copy()

    train_df["split"] = "TRAIN"
    val_df["split"] = "VAL"
    test_df["split"] = "TEST"

    os.makedirs(splits_dir, exist_ok=True)
    train_path = os.path.join(splits_dir, "train_split.csv")
    val_path = os.path.join(splits_dir, "val_split.csv")
    test_path = os.path.join(splits_dir, "test_split.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print("\n" + "=" * 60)
    print(" SIGNER-INDEPENDENT SPLITTING SUMMARY (ZERO LEAKAGE)")
    print("=" * 60)
    print(f"TRAIN SPLIT: {len(train_df)} samples ({len(train_df)/len(df)*100:.1f}%) | Signers ({len(train_signers)}): {sorted(train_signers)}")
    print(f"VAL SPLIT:   {len(val_df)} samples ({len(val_df)/len(df)*100:.1f}%) | Signers ({len(val_signers)}): {sorted(val_signers)}")
    print(f"TEST SPLIT:  {len(test_df)} samples ({len(test_df)/len(df)*100:.1f}%) | Signers ({len(test_signers)}): {sorted(test_signers)}")
    print("=" * 60)

    # Class balance check across splits
    print("\nClass sample distribution across splits:")
    for cid in range(10):
        c_name = train_df[train_df['class_id'] == cid]['class_label'].iloc[0] if cid in train_df['class_id'].values else f"Class_{cid}"
        n_tr = len(train_df[train_df['class_id'] == cid])
        n_va = len(val_df[val_df['class_id'] == cid])
        n_te = len(test_df[test_df['class_id'] == cid])
        print(f"  [{cid}] {c_name:<18}: Train={n_tr:>3}, Val={n_va:>2}, Test={n_te:>2} (Total: {n_tr+n_va+n_te})")

    print(f"\n[OK] Saved splits to: {splits_dir}")
    return train_path, val_path, test_path


def main():
    args = parse_args()
    split_dataset(args.manifest, args.splits_dir, args.train_ratio, args.val_ratio, args.seed)


if __name__ == "__main__":
    main()
