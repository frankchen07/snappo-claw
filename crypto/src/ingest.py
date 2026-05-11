"""Document ingestion pipeline + BM25 keyword search."""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


FRAMEWORK_PATTERNS = [
    ("trend_template", r"trend template|stage 2 uptrend|200.?day moving average|150.?day|200ma"),
    ("vcp", r"\bVCP\b|volatility contraction|tight consolidation|pivot point"),
    ("breakout", r"breakout|pivot high|above.{0,20}resistance|new high"),
    ("stop_loss", r"stop.?loss|stop level|invalidation|cut.{0,10}loss|below.{0,15}low"),
    ("position_sizing", r"position sizing|risk per trade|1%.{0,20}risk|2%.{0,20}risk|kelly|portfolio risk"),
    ("volume_analysis", r"volume.{0,20}average|above.?average volume|relative volume|volume spike|1\.5x"),
    ("canslim", r"CANSLIM|earnings growth|institutional|relative strength|market direction"),
    ("risk_reward", r"risk.?reward|r:r|profit target|1:2|1:3|reward.{0,10}risk"),
]


def _extract_text_from_pdf(filepath: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return ""


def _extract_text_from_json_chatgpt(data: dict) -> str:
    """Extract text from OpenAI ChatGPT conversation export format."""
    parts = []
    mapping = data.get("mapping", {})
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        content = msg.get("content", {})
        if isinstance(content, dict):
            for part in content.get("parts", []):
                if isinstance(part, str):
                    parts.append(part)
        elif isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def _extract_frameworks(text: str, source: str) -> list[dict]:
    """Heuristic: find sentences containing known framework keywords."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    entries = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        for framework_type, pattern in FRAMEWORK_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                entries.append({
                    "framework_type": framework_type,
                    "text": sentence,
                    "source": source,
                })
    return entries


def _file_hash(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


class DocumentIngester:
    def __init__(self, knowledge_dir: str):
        self.raw_dir = os.path.join(knowledge_dir, "raw")
        self.processed_dir = os.path.join(knowledge_dir, "processed")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        self._metadata_path = os.path.join(self.processed_dir, "metadata.json")
        self._frameworks_path = os.path.join(self.processed_dir, "frameworks.json")

    def _load_metadata(self) -> dict:
        if os.path.exists(self._metadata_path):
            with open(self._metadata_path) as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata: dict) -> None:
        with open(self._metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _load_frameworks(self) -> list[dict]:
        if os.path.exists(self._frameworks_path):
            with open(self._frameworks_path) as f:
                return json.load(f)
        return []

    def _save_frameworks(self, frameworks: list[dict]) -> None:
        with open(self._frameworks_path, "w") as f:
            json.dump(frameworks, f, indent=2)

    def ingest_all(self) -> dict:
        metadata = self._load_metadata()
        frameworks = self._load_frameworks()
        processed = 0
        errors = 0
        new_frameworks = 0

        for fname in os.listdir(self.raw_dir):
            fpath = os.path.join(self.raw_dir, fname)
            if not os.path.isfile(fpath):
                continue
            fhash = _file_hash(fpath)
            if metadata.get(fname) == fhash:
                continue  # already processed

            try:
                ext = Path(fname).suffix.lower()
                if ext == ".pdf":
                    text = _extract_text_from_pdf(fpath)
                elif ext == ".json":
                    with open(fpath) as f:
                        data = json.load(f)
                    text = _extract_text_from_json_chatgpt(data)
                else:
                    with open(fpath, encoding="utf-8", errors="replace") as f:
                        text = f.read()

                entries = _extract_frameworks(text, source=fname)
                frameworks.extend(entries)
                new_frameworks += len(entries)
                metadata[fname] = fhash
                processed += 1
            except Exception:
                errors += 1

        self._save_frameworks(frameworks)
        self._save_metadata(metadata)
        return {"processed": processed, "errors": errors, "new_frameworks": new_frameworks}


class FrameworkIndex:
    def __init__(self, knowledge_dir: str):
        frameworks_path = os.path.join(knowledge_dir, "processed", "frameworks.json")
        if os.path.exists(frameworks_path):
            with open(frameworks_path) as f:
                self._entries = json.load(f)
        else:
            self._entries = []

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self._entries:
            return []
        q_tokens = set(self._tokenize(query))
        scored = []
        for entry in self._entries:
            doc_tokens = self._tokenize(entry["text"])
            doc_set = set(doc_tokens)
            overlap = len(q_tokens & doc_set)
            if overlap > 0:
                tf = overlap / max(len(doc_tokens), 1)
                scored.append((tf, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]
