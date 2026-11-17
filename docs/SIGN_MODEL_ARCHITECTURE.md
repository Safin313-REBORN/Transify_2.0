# Transify — Sign Language Model Architecture & Temporal Modeling Specification
## 10-Class Bangladesh Sign Language (BdSL) Closed-Vocabulary System

**Document Version:** 2.0.0  
**Phase:** Phase 2 — Model Architecture Design  
**Input Modality:** 30-Frame Temporal Sequence of 162-Dimensional MediaPipe Holistic Vectors  
**Target Output:** 10 Communicative Expressions + Unknown/Idle Rejection  

---

## 1. Feature Representation & Input Topology

```
+----------------------------------------------------------------------------------------------------+
|                                    INPUT FEATURE TENSOR TOPOLOGY                                   |
|                                                                                                    |
|  Frame t in [0..29]:                                                                               |
|  [ Left Hand: 21 Landmarks x 3 ] + [ Right Hand: 21 Landmarks x 3 ] + [ Upper Pose: 12 Landmarks x 3]|
|  (63 Floats: x, y, z)              (63 Floats: x, y, z)               (36 Floats: x, y, z)         |
|  \______________________________________________________________________________________________/  |
|                                                  |                                                 |
|                                                  v                                                 |
|                               Feature Vector X_t in R^162 (Normalized)                             |
|                                                  |                                                 |
|                                                  v                                                 |
|                   Temporal Sequence Tensor X in R^(B x 30 x 162) (Shape: [Batch, T=30, D=162])    |
+----------------------------------------------------------------------------------------------------+
```

### 1.1 Mathematical Normalization Layer
Given raw coordinate landmarks $L_{i} = (x_i, y_i, z_i)$ from MediaPipe Holistic:
1. **Anatomical Center (Mid-Shoulder):**
   $$C = \frac{L_{\text{left\_shoulder}} + L_{\text{right\_shoulder}}}{2} = \frac{L_{11} + L_{12}}{2}$$
2. **Scale Factor (Inter-Shoulder Span):**
   $$S = \max(\|L_{11} - L_{12}\|_2, 10^{-6})$$
3. **Normalized Feature Vector:**
   $$L''_i = \frac{L_i - C}{S}, \quad \forall i \in \{\text{LeftHand}, \text{RightHand}, \text{UpperPose}\}$$
   This transformation renders the coordinate representation invariant to camera distance, zoom, and signer lateral position in the frame.

---

## 2. Candidate Temporal Architectures

```
+----------------------------------------------------------------------------------------------------+
|                                CANDIDATE ARCHITECTURAL COMPARISON                                  |
|                                                                                                    |
|  ARCHITECTURE A: Feature-Aggregated MLP Baseline                                                   |
|  Input [30 x 162] ---> [ Temporal Pooling: Mean, Std, Max, Min ] ---> [ 648D Vector ]             |
|                        ---> [ Dense(256) + BN + ReLU + Dropout(0.3) ]                              |
|                        ---> [ Dense(128) + BN + ReLU + Dropout(0.2) ]                              |
|                        ---> [ Dense(10) + Softmax ]                                                |
|                                                                                                    |
|  ARCHITECTURE B: 1D Temporal Convolutional Network (1D-CNN)                                        |
|  Input [30 x 162] ---> [ Conv1D(64, k=3, pad=1) + BN + ReLU ]                                      |
|                        ---> [ Conv1D(128, k=3, pad=1) + BN + ReLU + MaxPool(2) ]                   |
|                        ---> [ Conv1D(256, k=3, pad=1) + BN + ReLU + GlobalMaxPool ]                |
|                        ---> [ Dense(128) + Dropout(0.3) ] ---> [ Dense(10) + Softmax ]              |
|                                                                                                    |
|  ARCHITECTURE C: Bidirectional LSTM with Temporal Attention (BiLSTM)                               |
|  Input [30 x 162] ---> [ BiLSTM(hidden=128, layers=2, dropout=0.3) ]                                |
|                        ---> [ Forward h_t + Backward h_t in R^256 ]                                |
|                        ---> [ Self-Attention Layer: Softmax(v^T tanh(W h_t)) ]                     |
|                        ---> [ Context Vector c in R^256 ] ---> [ Dense(64) ]                        |
|                        ---> [ Dense(10) + Softmax ]                                                |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 Comparative Architecture Evaluation

| Criterion | Architecture A (MLP Baseline) | Architecture B (1D-CNN) | Architecture C (BiLSTM with Attention) |
|---|---|---|---|
| **Temporal Dynamics** | Summarized via static moments (mean, std, delta); loses frame ordering. | Local temporal filters capture short-term velocity changes. | Explicit sequential memory across all 30 frames; captures non-linear trajectories. |
| **Parameter Count** | $\sim 210\text{K}$ parameters | $\sim 340\text{K}$ parameters | $\sim 480\text{K}$ parameters |
| **CPU Latency (Single Trial)** | $< 1.0\text{ ms}$ | $\sim 2.5\text{ ms}$ | $\sim 4.5\text{ ms}$ |
| **Distinction Capability** | Good on static gestures (`OKAY`); poor on directional reversal (`YES` vs. `NO`). | High on rapid oscillations (`YES` vertical nod vs. `NO` horizontal wag). | Superior on complex compound trajectories (`I_NEED_HELP`, `I_DONT_UNDERSTAND`). |
| **Model Selection** | Fast benchmark baseline. | Candidate for edge/mobile deployment. | **Selected Primary Champion Architecture.** |

---

## 3. Unknown Gesture & Out-of-Distribution (OOD) Rejection

In real-world deployment, users perform casual movements, rest their hands, or execute gestures outside the 10 target classes. The system must not force non-target gestures into one of the 10 classes.

```
                  +----------------------------------------------+
                  | Input Prediction: Softmax Distribution P     |
                  +----------------------------------------------+
                                         |
                                         v
                  [ TEST 1: Spatial Motion Energy Check ]
                  E = sum_{t=1}^{T-1} || X_t - X_{t-1} ||_2
                                         |
                     +-------------------+-------------------+
                     | (E < 0.25: Signer is Idle/Stationary) | (E >= 0.25)
                     v                                       v
               [ REJECT: "IDLE" ]             [ TEST 2: Max Probability Check ]
                                              P_max = max(P)
                                                             |
                                      +----------------------+----------------------+
                                      | (P_max < 0.70)                              | (P_max >= 0.70)
                                      v                                             v
                           [ REJECT: "UNCONFIDENT" ]                 [ TEST 3: Entropy Check ]
                                                                     H = -sum P_c log(P_c)
                                                                                    |
                                                           +------------------------+------------------------+
                                                           | (H > 1.2: High Ambiguity) | (H <= 1.2: Sharp Peak)
                                                           v                           v
                                                 [ REJECT: "AMBIGUOUS" ]        [ ACCEPT PREDICTION ]
                                                 "Sign not recognized"          Output: Class + English Text
```

### 3.1 Mathematical Rejection Formulation
A prediction $\hat{y}$ is confirmed if and only if:
1. **Motion Threshold:**
   $$E_{\text{motion}} = \sum_{t=1}^{T-1} \|X_t - X_{t-1}\|_2 \ge \tau_{\text{motion}} \quad (\tau_{\text{motion}} = 0.25)$$
2. **Confidence Threshold:**
   $$P_{\max} = \max_{c \in \{0..9\}} P(c \mid X) \ge \tau_{\text{conf}} \quad (\tau_{\text{conf}} = 0.70)$$
3. **Entropy Calibration Threshold:**
   $$\mathcal{H}(P) = -\sum_{c=0}^9 P(c \mid X) \ln P(c \mid X) \le \tau_{\text{entropy}} \quad (\tau_{\text{entropy}} = 1.20)$$

If any condition fails, the system returns:
```json
{
  "recognized": false,
  "class_id": -1,
  "label": "UNKNOWN",
  "english_text": "Sign not recognized or not currently supported.",
  "confidence": 0.42,
  "supported": false,
  "rejection_reason": "Low confidence (0.42 < 0.70)"
}
```

---

## 4. Temporal Debounce and Consensus Filter

Single-frame predictions cause flickering text and repeated speech triggers. Transify applies a **Rolling Consensus Window**:
- Window size $W = 6$ consecutive inferences (at 30 FPS $\approx 200\text{ ms}$).
- A label $C$ is committed if and only if:
  $$\text{Count}(y_{t-5 \dots t} = C) \ge 5 \quad \text{and} \quad \text{MeanConfidence} \ge 0.75$$
- Speech synthesis is triggered **only once per committed gesture state**, requiring the user to return to neutral or change gesture before a new speech event fires.
