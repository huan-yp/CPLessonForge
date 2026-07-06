"""Browser management for problem fetching.

Provides two browser modes:
- Stealth persistent context (for CF/QOJ with Cloudflare)
- Normal context (for Luogu/AtCoder)
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth

DATA_DIR = Path(__file__).parent.parent / "data"


async def wait_for_cloudflare(page: Page, timeout: int = 30):
    """Wait for Cloudflare challenge to resolve. Prompts user if manual intervention needed."""
    await asyncio.sleep(3)
    title = await page.title()
    if "just a moment" in title.lower() or "请稍候" in title:
        print("⚠️  Cloudflare 验证触发，请在浏览器中完成验证")
        input("  完成后按 Enter 继续...")
        await asyncio.sleep(2)


class StealthBrowser:
    """Stealth browser with persistent context for Cloudflare-protected sites."""

    def __init__(self, profile_name: str):
        self.profile_dir = str(DATA_DIR / profile_name)
        self._context: BrowserContext | None = None
        self._stealth = Stealth(navigator_platform_override="MacIntel")
        self._pw_cm = None
        self._pw = None

    async def __aenter__(self):
        self._pw_cm = self._stealth.use_async(async_playwright())
        self._pw = await self._pw_cm.__aenter__()
        self._context = await self._pw.chromium.launch_persistent_context(
            self.profile_dir,
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )
        return self

    async def __aexit__(self, *args):
        if self._context:
            await self._context.close()
        if self._pw_cm:
            await self._pw_cm.__aexit__(*args)

    async def new_page(self) -> Page:
        return await self._context.new_page()

    @property
    def page(self) -> Page:
        return self._context.pages[0] if self._context.pages else None


class NormalBrowser:
    """Normal browser without stealth (for sites without Cloudflare)."""

    def __init__(self):
        self._browser = None
        self._context: BrowserContext | None = None
        self._pw_cm = None
        self._pw = None

    async def __aenter__(self):
        self._pw_cm = async_playwright()
        self._pw = await self._pw_cm.__aenter__()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, *args):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw_cm:
            await self._pw_cm.__aexit__(*args)

    async def new_page(self) -> Page:
        return await self._context.new_page()


class LuoguBrowser:
    """Browser for Luogu with persistent context for login state."""

    def __init__(self):
        self.profile_dir = str(DATA_DIR / "luogu_profile")
        self._context: BrowserContext | None = None
        self._pw_cm = None
        self._pw = None
        self._headed = False

    async def __aenter__(self):
        self._pw_cm = async_playwright()
        self._pw = await self._pw_cm.__aenter__()
        return self

    async def get_context(self, headed=False) -> BrowserContext:
        """Get or create context. Use headed=True when login is needed."""
        if self._context and self._headed == headed:
            return self._context
        if self._context:
            await self._context.close()
        self._headed = headed
        self._context = await self._pw.chromium.launch_persistent_context(
            self.profile_dir,
            headless=not headed,
            viewport={"width": 1280, "height": 900},
        )
        return self._context

    async def __aexit__(self, *args):
        if self._context:
            await self._context.close()
        if self._pw_cm:
            await self._pw_cm.__aexit__(*args)
