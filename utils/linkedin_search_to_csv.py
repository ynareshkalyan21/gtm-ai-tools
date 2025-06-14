"""Export LinkedIn profile URLs from Google search results into a CSV for outreach."""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import json
from pathlib import Path
from urllib.parse import urlparse

from utils.common import search_google_serper, extract_user_linkedin_page
from utils.find_a_user_by_name_and_keywords import (
    LeadSearchResult,
    get_structured_output,
)

DEFAULT_QUERY = 'site:linkedin.com/in "CEO"'


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def linkedin_search_to_csv(query: str, number_of_results: int, output_file: str) -> None:
    """Search Google for LinkedIn profile URLs and write them to a CSV."""

    query = query.strip() or DEFAULT_QUERY
    results = asyncio.run(search_google_serper(query, number_of_results))
    infos: list[LeadSearchResult] = []

    for item in results:
        link = item.get("link", "")
        if not link:
            continue
        parsed_url = urlparse(link)
        text = " ".join(
            [item.get("title", ""), item.get("subtitle", ""), item.get("snippet", "")] 
        ).strip()
        structured = asyncio.run(get_structured_output(text))
        if "linkedin.com/in" in (parsed_url.netloc + parsed_url.path):
            structured.user_linkedin_url = extract_user_linkedin_page(link)
            infos.append(structured)

    fieldnames = [
        "first_name",
        "last_name",
        "full_name",
        "job_title",
        "linkedin_follower_count",
        "lead_location",
        "summary_about_lead",
        "user_linkedin_url",
    ]
    with open(output_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for info in infos:
            writer.writerow(json.loads(info.model_dump_json()))

    logger.info("Wrote %d LinkedIn URLs to %s", len(infos), output_file)


def linkedin_search_to_csv_from_csv(input_file: str | Path, output_file: str | Path) -> None:
    """Run Google searches from a CSV and aggregate results.

    The ``input_file`` must contain ``search_query`` and ``number_of_responses``
    columns. The aggregated LinkedIn profile URLs are written to ``output_file``.
    """

    in_path = Path(input_file)
    out_path = Path(output_file)

    with in_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        raw_fieldnames = reader.fieldnames or []
        fieldnames = [f.strip() for f in raw_fieldnames]
        if "search_query" not in fieldnames or "number_of_responses" not in fieldnames:
            raise ValueError("upload csv with these two columns: search_query and number_of_responses")
        rows = list(reader)

    aggregated: list[LeadSearchResult] = []
    for row in rows:
        query = (row.get("search_query") or "").strip() or DEFAULT_QUERY
        try:
            num = int(row.get("number_of_responses") or 10)
        except ValueError:
            num = 10
        results = asyncio.run(search_google_serper(query, num))
        for item in results:
            link = item.get("link", "")
            if not link:
                continue
            parsed_url = urlparse(link)
            text = " ".join(
                [item.get("title", ""), item.get("subtitle", ""), item.get("snippet", "")] 
            ).strip()
            structured = asyncio.run(get_structured_output(text))
            if "linkedin.com/in" in (parsed_url.netloc + parsed_url.path):
                structured.user_linkedin_url = extract_user_linkedin_page(link)
                aggregated.append(structured)

    fieldnames = [
        "first_name",
        "last_name",
        "full_name",
        "job_title",
        "linkedin_follower_count",
        "lead_location",
        "summary_about_lead",
        "user_linkedin_url",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for info in aggregated:
            writer.writerow(json.loads(info.model_dump_json()))

    logger.info("Wrote %d LinkedIn URLs to %s", len(aggregated), out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Google via Serper.dev for LinkedIn profile URLs and output them to CSV"
    )
    parser.add_argument("query", help="Google search query")
    parser.add_argument("output_file", help="CSV file to create")
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=10,
        help="Number of search results to fetch",
    )
    args = parser.parse_args()

    query = args.query.strip() or DEFAULT_QUERY
    linkedin_search_to_csv(query, args.num, args.output_file)


if __name__ == "__main__":
    main()

