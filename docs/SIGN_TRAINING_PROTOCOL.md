# Transify — Sign Language Training Protocol & Optimization Specification
## 10-Class Bangladesh Sign Language (BdSL) Closed-Vocabulary System

**Document Version:** 2.0.0  
**Phase:** Phase 2 — Model Training & Optimization  
**Training Regime:** Signer-Independent Leave-Signers-Out (LSO) Partitioning  

---

## 1. Signer-Independent Splitting Formulation

To evaluate true generalization to previously unseen human signers, Transify strictly prohibits random frame or random sequence distribution across splits:

```
+----------------------------------------------------------------------------------------------------+
|                                SIGNER-INDEPENDENT PARTITIONING (LSO)                               |
|                                                                                                    |
| Total Available Signers Cohort: S001 through S008 (8 Independent Signers)                          |
|                                                                                                    |
|   [ TRAINING SPLIT: 75% ]            [ VALIDATION SPLIT: 12.5% ]        [ TEST SPLIT: 12.5% ]      |
|   Signers: S001, S002, S003,         Signer: S007                       Signer: S008               |
|            S004, S005, S006          (Early Stopping & Hyperparameter   (Blind Benchmark Reporting |
|   (Model Weights Optimization)        Tuning Checkpoints)                Held-Out Evaluation)      |
+----------------------------------------------------------------------------------------------------+
```

### 1.1 Non-Leakage Enforcement
- No video trial, landmark tensor, or augmented variant originating from Signer `S007` or `S008` is ever exposed to the training process.
- All temporal sequences remain intact; zero slicing across split boundaries.

---

## 2. Hyperparameter and Training Configuration

| Hyperparameter | Value | Scientific Justification |
|---|---|---|
| **Batch Size ($B$)** | 32 | Balanced gradient estimate for small-to-medium sequence batches. |
| **Sequence Length ($T$)**| 30 Frames | Corresponds to 1.0 second at 30 FPS, fully capturing BdSL phrase trajectories. |
| **Feature Dimension ($D$)**| 162 Floats | Dual hands ($42 \times 3$) + Upper-body pose ($12 \times 3$). |
| **Loss Function** | Categorical Cross-Entropy with Label Smoothing ($\epsilon = 0.05$) | Prevents overconfident softmax saturation and improves calibration. |
| **Optimizer** | AdamW ($\beta_1=0.9, \beta_2=0.999$) | Decoupled weight decay regularization. |
| **Weight Decay ($\lambda$)**| $1 \times 10^{-4}$ | Regularizes dense layers to suppress co-adaptation. |
| **Initial Learning Rate ($\eta$)**| $1 \times 10^{-3}$ | Standard stable initial learning rate for AdamW. |
| **Learning Rate Schedule**| Cosine Annealing with Warm-up (5 epochs) | Smooth decay to $\eta_{\min} = 10^{-5}$ without abrupt step drops. |
| **Max Training Epochs** | 40 Epochs | Sufficient for convergence without overfitting. |
| **Early Stopping** | Patience = 8 Epochs on Validation Loss | Halts training automatically when validation loss fails to improve. |
| **Random Seed** | Fixed `SEED = 42` | Ensures deterministic parameter initialization and data shuffling. |

---

## 3. Training-Time Coordinate Data Augmentation

Data augmentation is applied **STRICTLY to the Training Split** during runtime batches; the Validation and Test splits remain completely untouched:

1. **Random 3D Spatial Rotation:**
   Apply rotation matrix $\mathbf{R} \in \text{SO}(3)$ with random angles $\theta_x, \theta_y, \theta_z \sim \mathcal{U}(-8^\circ, +8^\circ)$ to simulate minor camera orientation deviations:
   $$X_{\text{aug}} = X \mathbf{R}^T$$
2. **Random Anthropometric Scale Perturbation:**
   Scale hand and torso coordinates by $s \sim \mathcal{U}(0.90, 1.10)$ to simulate varying signer body sizes:
   $$X_{\text{aug}} = s \cdot X$$
3. **Additive Sensor Gaussian Noise:**
   Add zero-mean Gaussian jitter to simulate webcam sensor noise:
   $$X_{\text{aug}} = X + \mathcal{N}(0, 0.005)$$
4. **Temporal Speed Jitter (Time Warping):**
   Subsample or interpolate temporal indices to simulate $\pm 15\%$ variations in signing speed.

---

## 4. Checkpointing and Versioning Protocol

1. **Best Model Selection:** The training harness tracks validation loss and validation Macro F1 score after every epoch.
2. **Checkpoint Directory:** Checkpoints are saved to `models/sign/checkpoints/` with naming convention:
   `bdsl_model_<arch>_epoch<EE>_valf1_<F1>.pt`
3. **Model Artifact Export:** The champion model is serialized as:
   - Primary PyTorch / Scikit-Learn weights (`models/sign/bdsl_champion_model.pkl` / `.pth`)
   - Exported portable ONNX model (`models/sign/bdsl_champion_model.onnx`)
   - Complete metadata manifest (`models/sign/model_metadata.json`) containing class mapping, input shapes, and training commit hash.
