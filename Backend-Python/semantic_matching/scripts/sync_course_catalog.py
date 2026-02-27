import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from core.course_catalog_sync import sync_catalog
from core.course_recommender import CourseRecommender

load_dotenv(BACKEND_ROOT / ".env")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Sync local course catalog and rebuild FAISS index."
    )
    parser.add_argument(
        "--output",
        default=os.getenv("COURSE_CATALOG_PATH", "data/course_catalog.json"),
        help="Path to normalized course catalog JSON.",
    )
    parser.add_argument(
        "--source-url",
        action="append",
        default=None,
        help="Source URL (JSON/CSV). Can be set multiple times.",
    )
    parser.add_argument(
        "--source-file",
        action="append",
        default=None,
        help="Source file path (JSON/CSV). Can be set multiple times.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=25,
        help="HTTP timeout in seconds for remote URLs.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    output_path = Path(args.output)

    payload = sync_catalog(
        output_path=output_path,
        source_urls=args.source_url,
        source_files=args.source_file,
        timeout=args.timeout,
    )

    # Rebuild index from the newly synced catalog.
    recommender = CourseRecommender()
    recommender.refresh_from_disk(force_rebuild=True)

    print(
        json.dumps(
            {
                "success": True,
                "output": str(output_path.resolve()),
                "course_count": payload.get("course_count", 0),
                "sources": payload.get("sources", []),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
