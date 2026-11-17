"""
Transify — BdSL Sign Model Export & Serialization Utility
Exports the trained model weights, feature scaler parameters, and metadata
into portable runtime formats for edge/CPU inference and provides ONNX export hooks.
"""

import os
import json
import pickle
import argparse
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Transify Model Exporter")
    parser.add_argument("--model_path", type=str, default="models/sign/bdsl_champion_model.pkl", help="Trained model path")
    parser.add_argument("--scaler_path", type=str, default="models/sign/scaler.pkl", help="Fitted scaler path")
    parser.add_argument("--out_dir", type=str, default="models/sign/exported", help="Export destination directory")
    return parser.parse_args()


def export_portable_bundle(model_path: str, scaler_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    # 1. Export Scaler Mean & Scale vectors to JSON and NumPy
    scaler_params = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "var": scaler.var_.tolist(),
        "n_features_in": int(scaler.n_features_in_)
    }
    scaler_json_path = os.path.join(out_dir, "scaler_params.json")
    with open(scaler_json_path, "w", encoding="utf-8") as f:
        json.dump(scaler_params, f, indent=2)

    # 2. Export Model Bundle Manifest
    bundle_manifest = {
        "model_type": type(model).__name__,
        "n_classes": len(model.classes_),
        "classes": [int(c) for c in model.classes_],
        "n_features_in": int(model.n_features_in_),
        "input_feature_dim": 972,
        "temporal_sequence_shape": [30, 162],
        "exported_timestamp": "2026-11-14T12:00:00Z"
    }

    manifest_path = os.path.join(out_dir, "model_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(bundle_manifest, f, indent=2)

    # 3. Save optimized inference package
    bundle_pkl_path = os.path.join(out_dir, "bdsl_model_bundle.pkl")
    with open(bundle_pkl_path, "wb") as f:
        pickle.dump({"model": model, "scaler": scaler, "manifest": bundle_manifest}, f)

    print(f"[OK] Exported portable scaler params: {scaler_json_path}")
    print(f"[OK] Exported bundle manifest:        {manifest_path}")
    print(f"[OK] Exported inference bundle:       {bundle_pkl_path}")

    # 4. Check for ONNX runtime conversion
    try:
        import skl2onnx
        from skl2onnx.common.data_types import FloatTensorType
        initial_type = [('float_input', FloatTensorType([None, 972]))]
        onx = skl2onnx.convert_sklearn(model, initial_types=initial_type)
        onnx_path = os.path.join(out_dir, "bdsl_model.onnx")
        with open(onnx_path, "wb") as f:
            f.write(onx.SerializeToString())
        print(f"[OK] Exported native ONNX model:      {onnx_path}")
    except ImportError:
        print("[INFO] skl2onnx not installed in local environment.")
        print("[INFO] Model bundle successfully exported in native portable Python/NumPy runtime format.")
        print("[INFO] For ONNX binary export, run on Google Colab or install skl2onnx with: pip install skl2onnx onnx")

    return bundle_pkl_path


def main():
    args = parse_args()
    print("=" * 60)
    print(" Transify BdSL Model Exporter")
    print(f" Source Model:  {args.model_path}")
    print(f" Source Scaler: {args.scaler_path}")
    print(f" Output Dir:    {args.out_dir}")
    print("=" * 60)
    export_portable_bundle(args.model_path, args.scaler_path, args.out_dir)


if __name__ == "__main__":
    main()
