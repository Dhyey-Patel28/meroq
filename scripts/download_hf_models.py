from __future__ import annotations

from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except Exception as exc:
    raise SystemExit("Install NLP requirements first: python -m pip install -r requirements-nlp.txt") from exc

from src.news_sentiment import HF_MODEL_IDS


def main() -> None:
    print("Downloading/caching Hugging Face sentiment models...")
    for name, repo_id in HF_MODEL_IDS.items():
        print(f"- {name}: {repo_id}")
        path = snapshot_download(repo_id=repo_id, repo_type="model")
        print(f"  cached at: {Path(path)}")
    print("Done. Meroq can now load these models from the local Hugging Face cache.")


if __name__ == "__main__":
    main()
