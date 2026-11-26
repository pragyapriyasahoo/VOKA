import json
from pathlib import Path


def load_dataset(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    print("Use load_dataset(path) to prepare a training dataset.")
