"""Runs Scrapy in a subprocess to avoid Twisted reactor conflicts with FastAPI.

Each scrape job spawns a fresh Python subprocess that executes a Scrapy crawl,
writes results to a temp JSON file, then exits. The API reads the results and
updates the job store.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from . import jobs


async def run_scrape(
    job_id: str,
    url: str,
    selectors: dict[str, str],
    selector_type: str,
    follow_links: bool,
    max_items: int,
    encoding_hint: str,
    user_agent: str,
) -> None:
    jobs.update(job_id, status="running")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        out_path = tmp.name

    spider_module = str(Path(__file__).parent / "spiders" / "generic_spider.py")

    cmd = [
        sys.executable,
        "-c",
        _build_runner_script(
            spider_module=spider_module,
            url=url,
            selectors=json.dumps(selectors),
            selector_type=selector_type,
            follow_links=str(follow_links).lower(),
            max_items=str(max_items),
            encoding_hint=encoding_hint,
            user_agent=user_agent,
            out_path=out_path,
        ),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode(errors="replace").strip())

        raw = Path(out_path).read_text(encoding="utf-8")
        items = json.loads(raw) if raw.strip() else []
        jobs.update(job_id, status="complete", items=items)

    except TimeoutError:
        jobs.update(job_id, status="failed", error="Scrape timed out after 60 seconds.")
    except Exception as exc:
        jobs.update(job_id, status="failed", error=str(exc))
    finally:
        Path(out_path).unlink(missing_ok=True)


def _build_runner_script(
    spider_module: str,
    url: str,
    selectors: str,
    selector_type: str,
    follow_links: str,
    max_items: str,
    encoding_hint: str,
    user_agent: str,
    out_path: str,
) -> str:
    # All args are passed as string literals embedded in the script to avoid shell injection.
    # Each value is repr()-encoded so arbitrary characters are safely escaped.
    return f"""
import sys, json
sys.path.insert(0, {repr(str(Path(__file__).parent.parent.parent))})

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Load the spider class directly from its module path
import importlib.util
spec = importlib.util.spec_from_file_location("generic_spider", {repr(spider_module)})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
GenericSpider = mod.GenericSpider

settings = get_project_settings()
settings.update({{
    "FEEDS": {{{repr(out_path)}: {{"format": "json", "encoding": {repr(encoding_hint)}}}}},
    "FEED_EXPORT_ENCODING": {repr(encoding_hint)},
    "USER_AGENT": {repr(user_agent)},
    "LOG_ENABLED": False,
    "ROBOTSTXT_OBEY": True,
    "CLOSESPIDER_ITEMCOUNT": {repr(max_items)},
    "DOWNLOAD_TIMEOUT": 30,
}})

process = CrawlerProcess(settings)
process.crawl(
    GenericSpider,
    start_url={repr(url)},
    selectors={repr(selectors)},
    selector_type={repr(selector_type)},
    follow_links={repr(follow_links)},
)
process.start()
"""
