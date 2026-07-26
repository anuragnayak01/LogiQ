"""
CLI ingestion -- only needed if you're loading documents from local files.
For deploy-only workflows, use the POST /admin/ingest or /admin/seed API
routes instead (see README.md) -- no local Python environment required.

Usage:
    python -m app.ingest --path ../sample_docs --doc-type sop
    python -m app.ingest --path ../sample_docs/single_file.md --doc-type policy
"""

import argparse
from pathlib import Path

from app.ingestion import ingest_text


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the KB agent's pgvector store.")
    parser.add_argument("--path", required=True, help="File or directory of .md/.txt documents")
    parser.add_argument(
        "--doc-type",
        default="sop",
        choices=["sop", "policy", "training"],
        help="Document category (default: sop)",
    )
    args = parser.parse_args()

    target = Path(args.path)
    files = [target] if target.is_file() else sorted(target.glob("*.md")) + sorted(target.glob("*.txt"))

    if not files:
        print(f"No .md/.txt files found at {target}")
        return

    for f in files:
        result = ingest_text(f.stem, args.doc_type, f.read_text(encoding="utf-8"), source_path=str(f))
        print(f"Ingested '{f.name}' -> document_id={result['document_id']}, chunks={result['chunks']}")


if __name__ == "__main__":
    main()
