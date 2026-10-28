"""OFFLINE training script for the optional Edge AI -> model.json.

Usage: python train_edge_model.py data.csv [max_rows_per_class]
CSV columns: url,label  (label: bad/good, or 1/0)
Example free dataset: github.com/faizann24/Using-machine-learning-to-detect-malicious-URLs (data/data.csv)
Pure standard library: SGD logistic regression.
"""
import csv
import datetime
import json
import math
import random
import sys

from edge_ai import MODEL_PATH, features

DIM = 8192
N_NUMERIC = 8
EPOCHS = 4
LR = 0.3
L2 = 1e-6


def load(path, per_class):
    good, bad = [], []
    with open(path, encoding="utf-8", errors="ignore", newline="") as f:
        for row in csv.DictReader(f):
            url, lab = (row.get("url") or "").strip(), (row.get("label") or "").strip().lower()
            if not url:
                continue
            if lab in ("bad", "1", "phishing", "malicious"):
                bad.append(url)
            elif lab in ("good", "0", "benign", "legitimate"):
                good.append(url)
    random.seed(42)
    random.shuffle(good)
    random.shuffle(bad)
    n = min(per_class, len(good), len(bad))
    data = [(u, 0) for u in good[:n]] + [(u, 1) for u in bad[:n]]
    random.shuffle(data)
    return data


def sigmoid(z):
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def main():
    path = sys.argv[1]
    per_class = int(sys.argv[2]) if len(sys.argv) > 2 else 40000
    data = load(path, per_class)
    split = int(len(data) * 0.8)
    train, test = data[:split], data[split:]
    print(f"train={len(train)} test={len(test)}")
    X_train = [(features(u, DIM), y) for u, y in train]
    w = [0.0] * (DIM + N_NUMERIC)
    for ep in range(EPOCHS):
        random.shuffle(X_train)
        lr = LR / (1 + ep)
        for x, y in X_train:
            g = sigmoid(sum(w[i] * v for i, v in x.items())) - y
            for i, v in x.items():
                w[i] -= lr * (g * v + L2 * w[i])
        print(f"epoch {ep + 1} done")
    tp = fp = fn = tn = 0
    for u, y in test:
        x = features(u, DIM)
        p = sigmoid(sum(w[i] * v for i, v in x.items())) >= 0.5
        tp += p and y
        fp += p and not y
        fn += (not p) and y
        tn += (not p) and (not y)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    acc = (tp + tn) / max(len(test), 1)
    print(f"precision={precision:.3f} recall={recall:.3f} accuracy={acc:.3f}")
    model = {
        "dim": DIM, "n_numeric": N_NUMERIC,
        "weights": {str(i): round(v, 2) for i, v in enumerate(w) if abs(round(v, 2)) > 0},
        "meta": {"trained": datetime.date.today().isoformat(), "train_rows": len(train),
                 "test_rows": len(test), "precision": round(precision, 3),
                 "recall": round(recall, 3), "accuracy": round(acc, 3),
                 "model": "logistic regression, hashed char 3-grams + 7 numeric features"},
    }
    MODEL_PATH.write_text(json.dumps(model, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {MODEL_PATH} ({MODEL_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
