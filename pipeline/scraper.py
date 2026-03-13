"""
Playwright-based headless browser scraper for JS-rendered VC portfolio sites.

Handles dynamic content loading, rate limiting, retries, and batch scraping
across multiple VC firm websites.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_MS = 30_000
NAVIGATION_TIMEOUT_MS = 45_000
RATE_LIMIT_MIN_SECONDS = 2.0
RATE_LIMIT_MAX_SECONDS = 5.0
MAX_RETRIES = 3

# Common selectors that indicate a portfolio page has fully loaded
PORTFOLIO_READY_SELECTORS = [
    "[class*='portfolio']",
    "[class*='company']",
    "[class*='startup']",
    "[data-component*='portfolio']",
    "main",
    "#content",
    "article",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15"
    ),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScrapeResult:
    """Result from scraping a single URL."""

    url: str
    html: str = ""
    success: bool = False
    error: str | None = None
    elapsed_seconds: float = 0.0


@dataclass
class VCScrapeResult:
    """Result from scraping a VC firm's portfolio pages."""

    vc_slug: str
    vc_name: str
    results: list[ScrapeResult] = field(default_factory=list)

    @property
    def all_html(self) -> str:
        """Concatenate all successful page HTML."""
        return "\n".join(r.html for r in self.results if r.success)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class VCScraper:
    """Playwright-based scraper for JS-rendered VC portfolio websites.

    Usage::

        async with VCScraper() as scraper:
            html = await scraper.scrape_portfolio("https://a16z.com/portfolio")

    Or manually::

        scraper = VCScraper()
        await scraper.init()
        html = await scraper.scrape_portfolio(url)
        await scraper.close()
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        rate_limit_range: tuple[float, float] = (
            RATE_LIMIT_MIN_SECONDS,
            RATE_LIMIT_MAX_SECONDS,
        ),
    ) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._rate_limit_range = rate_limit_range
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._initialized = False

    # -- Lifecycle -----------------------------------------------------------

    async def init(self) -> None:
        """Launch the browser and create a default context."""
        if self._initialized:
            return

        logger.info("Initializing Playwright browser (headless=%s)", self._headless)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1440, "height": 900},
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        self._context.set_default_timeout(self._timeout_ms)
        self._context.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
        self._initialized = True
        logger.info("Playwright browser initialized")

    async def close(self) -> None:
        """Shut down the browser and Playwright."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False
        logger.info("Playwright browser closed")

    async def __aenter__(self) -> "VCScraper":
        await self.init()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # -- Core scraping -------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((TimeoutError, Exception)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def scrape_portfolio(self, url: str) -> str:
        """Scrape a single portfolio URL and return the page HTML.

        Navigates to the URL, waits for JS rendering to complete, scrolls to
        trigger lazy-loaded content, and returns the full page HTML.

        Args:
            url: The portfolio page URL.

        Returns:
            The full HTML content of the page.

        Raises:
            RuntimeError: If the scraper has not been initialized.
            TimeoutError: If the page fails to load within the timeout.
        """
        if not self._initialized or self._context is None:
            raise RuntimeError("Scraper not initialized. Call init() or use as context manager.")

        page: Page = await self._context.new_page()
        try:
            logger.info("Navigating to %s", url)
            response = await page.goto(url, wait_until="domcontentloaded")

            if response and response.status >= 400:
                raise RuntimeError(f"HTTP {response.status} for {url}")

            # Wait for any portfolio-like content to appear
            await self._wait_for_content(page)

            # Scroll to trigger lazy loading
            await self._scroll_page(page)

            # Small extra wait for any post-scroll rendering
            await page.wait_for_timeout(1500)

            html = await page.content()
            logger.info(
                "Scraped %s — %d chars of HTML",
                url,
                len(html),
            )
            return html

        finally:
            await page.close()

    async def scrape_batch(self, vc_configs: list[dict]) -> list[VCScrapeResult]:
        """Scrape portfolio pages for multiple VC firms sequentially.

        Each VC config dict should contain at minimum:
            - slug: str
            - name: str
            - portfolio_urls: list[str]

        Rate limiting is applied between requests to be respectful.

        Args:
            vc_configs: List of VC configuration dicts from vc_list.yaml.

        Returns:
            List of VCScrapeResult objects, one per VC.
        """
        if not self._initialized:
            await self.init()

        results: list[VCScrapeResult] = []

        for vc in vc_configs:
            slug = vc.get("slug", "unknown")
            name = vc.get("name", slug)
            urls = vc.get("portfolio_urls", [])

            if not urls:
                logger.warning("No portfolio URLs configured for VC %r, skipping", slug)
                continue

            vc_result = VCScrapeResult(vc_slug=slug, vc_name=name)

            for url in urls:
                result = await self._scrape_single(url)
                vc_result.results.append(result)

                # Rate limiting between requests
                delay = random.uniform(*self._rate_limit_range)
                logger.debug("Rate limiting: sleeping %.1fs", delay)
                await asyncio.sleep(delay)

            logger.info(
                "VC %r: scraped %d/%d URLs successfully",
                slug,
                vc_result.success_count,
                len(urls),
            )
            results.append(vc_result)

        return results

    # -- Internal helpers ----------------------------------------------------

    async def _scrape_single(self, url: str) -> ScrapeResult:
        """Scrape a single URL, wrapping errors into ScrapeResult."""
        import time

        start = time.monotonic()
        try:
            html = await self.scrape_portfolio(url)
            elapsed = time.monotonic() - start
            return ScrapeResult(
                url=url, html=html, success=True, elapsed_seconds=round(elapsed, 2)
            )
        except RetryError as exc:
            elapsed = time.monotonic() - start
            error_msg = f"All retries exhausted: {exc}"
            logger.error("Failed to scrape %s after retries: %s", url, error_msg)
            return ScrapeResult(
                url=url, error=error_msg, elapsed_seconds=round(elapsed, 2)
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            error_msg = str(exc)
            logger.error("Failed to scrape %s: %s", url, error_msg)
            return ScrapeResult(
                url=url, error=error_msg, elapsed_seconds=round(elapsed, 2)
            )

    async def _wait_for_content(self, page: Page) -> None:
        """Wait for meaningful content to appear on the page.

        Tries several common selectors and falls back to network idle.
        """
        for selector in PORTFOLIO_READY_SELECTORS:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                logger.debug("Found content with selector %r", selector)
                return
            except Exception:
                continue

        # Fallback: wait for network to settle
        logger.debug("No portfolio selectors found, waiting for network idle")
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            logger.debug("Network idle timeout; proceeding with current content")

    async def _scroll_page(self, page: Page) -> None:
        """Scroll the page incrementally to trigger lazy-loaded content."""
        try:
            scroll_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")
            current_position = 0
            scroll_step = viewport_height * 0.8

            while current_position < scroll_height:
                current_position += scroll_step
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await page.wait_for_timeout(500)

                # Recheck scroll height in case new content loaded
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > scroll_height:
                    scroll_height = new_height

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
        except Exception as exc:
            logger.debug("Scroll error (non-fatal): %s", exc)
