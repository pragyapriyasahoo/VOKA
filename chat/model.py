import json
import os
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)
from sklearn.preprocessing import LabelEncoder

MODEL_NAME = "distilbert-base-uncased"
DATASET_PATH = "voka/data/emotional_support.json"
OUTPUT_DIR = "emotion_model"
NUM_EPOCHS = 5
BATCH_SIZE = 8
MAX_LENGTH = 64

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

texts = []
labels = []

for item in raw_data:
    emotion = item["emotion"]

    texts.extend([
        f"I feel {emotion}",
        f"I am feeling {emotion}",
        f"I feel very {emotion}",
        f"I am {emotion}",
    ])
    labels.extend([emotion] * 4)

label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)

num_labels = len(label_encoder.classes_)

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(os.path.join(OUTPUT_DIR, "label_map.json"), "w") as f:
    json.dump(
        {i: label for i, label in enumerate(label_encoder.classes_)},
        f,
        indent=2
    )

class EmotionDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long)
        }

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=num_labels
)

dataset = EmotionDataset(texts, encoded_labels, tokenizer)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    logging_steps=10,
    save_strategy="epoch",
    learning_rate=5e-5,
    weight_decay=0.01,
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset
)

trainer.train()

model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n[OK] Emotion classifier training complete.")
print(f"[INFO] Model saved to: {OUTPUT_DIR}")