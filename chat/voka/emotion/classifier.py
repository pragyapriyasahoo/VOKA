import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
_CLASSIFIER_CACHE = {}


def get_classifier(model_dir: Path | None = None):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from voka.config.settings import EMOTION_MODEL_DIR

    directory = Path(model_dir or EMOTION_MODEL_DIR)
    cache_key = str(directory.resolve())
    if cache_key not in _CLASSIFIER_CACHE:
        tokenizer = AutoTokenizer.from_pretrained(directory)
        model = AutoModelForSequenceClassification.from_pretrained(directory)
        model.eval()
        _CLASSIFIER_CACHE[cache_key] = (tokenizer, model)
    return _CLASSIFIER_CACHE[cache_key]


def predict_emotion(text: str, model_dir: Path | None = None) -> str | None:
    try:
        import torch
        from voka.config.settings import EMOTION_MODEL_DIR
        directory = Path(model_dir or EMOTION_MODEL_DIR)
        with open(directory / "label_map.json", encoding="utf-8") as file:
            labels = {int(key): value for key, value in json.load(file).items()}
        tokenizer, model = get_classifier(directory)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=64)
        with torch.no_grad():
            prediction = torch.argmax(model(**inputs).logits, dim=1).item()
        return labels[prediction]
    except Exception as error:
        logger.warning("Emotion inference unavailable: %s", error)
        return None
