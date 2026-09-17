from typing import Dict, Any, List


def calculate_binary_metrics(y_true: List[bool], y_pred: List[bool]) -> Dict[str, float]:
    """Calculates Precision, Recall, F1 score, and Accuracy for binary classification."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t is True and p is True)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t is False and p is True)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t is True and p is False)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t is False and p is False)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1 * 100, 2),
        "accuracy": round(accuracy * 100, 2)
    }
