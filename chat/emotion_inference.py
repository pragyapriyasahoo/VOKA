import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "emotion_model"
DEVICE = "cpu"

with open(f"{MODEL_DIR}/label_map.json", "r", encoding="utf-8") as f:
    label_map = json.load(f)

id_to_emotion = {int(k): v for k, v in label_map.items()}

hf_tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(DEVICE)
model.eval()

def predict_emotion(text: str) -> str:
    inputs = hf_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=64
    )

    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_id = torch.argmax(logits, dim=1).item()

    return id_to_emotion[predicted_id]

if __name__ == "__main__":
    print("Emotion inference ready. Type 'exit' to quit.\n")

    while True:
        text = input("You: ").strip()
        if text.lower() == "exit":
            break

        emotion = predict_emotion(text)
        print(f"Detected emotion: {emotion}\n")