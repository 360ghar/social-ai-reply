import csv
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.analytics import HandleMetric


def export_handle_metrics(
    metrics: list[HandleMetric],
    query_name: str,
    output_dir: str = "./exports",
) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"{query_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = output_path / filename

    with file_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["instagram_user_id", "username", "metric_count", "distinct_profiles"],
        )
        writer.writeheader()
        for row in metrics:
            writer.writerow(row.model_dump())
    return str(file_path.resolve())
