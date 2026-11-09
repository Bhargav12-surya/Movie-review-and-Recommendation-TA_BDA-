"""Temperature scaling fitted only on the dedicated calibration split."""
import math
from numbers import Integral


def softmax(logits, temperature: float = 1.0) -> list[list[float]]:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("Temperature must be positive and finite.")
    rows, width = [], None
    for row in logits:
        values = [float(value) / temperature for value in row]
        if len(values) < 2 or not all(math.isfinite(value) for value in values):
            raise ValueError("Finite, multiclass logits are required.")
        width = width or len(values)
        if len(values) != width:
            raise ValueError("Inconsistent class dimensions.")
        maximum = max(values)
        exps = [math.exp(value - maximum) for value in values]
        total = sum(exps)
        rows.append([value / total for value in exps])
    return rows


def fit_temperature(logits, y_true) -> float:
    logits, y_true = list(logits), list(y_true)
    if not logits or len(logits) != len(y_true):
        raise ValueError("Calibration logits/labels must be nonempty and aligned.")
    width = len(logits[0])
    if any(isinstance(label, bool) or not isinstance(label, Integral) or not 0 <= label < width for label in y_true):
        raise ValueError("Invalid calibration label indices.")
    y_true = [int(label) for label in y_true]
    # Fixed one-dimensional search; no test set access or fabricated confidence.
    temperatures = [math.exp(math.log(0.05) + index * (math.log(20.0) - math.log(0.05)) / 160)
                    for index in range(161)] + [1.0]
    def objective(temperature):
        probabilities = softmax(logits, temperature)
        return -sum(math.log(max(row[label], 1e-15)) for row, label in zip(probabilities, y_true)) / len(y_true)
    return min(temperatures, key=objective)
