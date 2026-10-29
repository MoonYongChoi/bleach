"""새 체험단 사이트 구조 조사용 — 커넥터를 만들기 전에 GitHub Actions에서 돌려 로그로 본다.

    python probe.py https://example.com/list

원본 HTML(서버 렌더링 여부)과 브라우저 렌더링 결과를 둘 다 보고, 반복되는 카드 마크업과
페이지가 부르는 JSON/XHR 주소를 출력한다. DB는 건드리지 않는다.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}


def card_candidates(soup: BeautifulSoup, base: str) -> None:
    links = [a for a in soup.select("a[href]") if a.get_text(strip=True) or a.select_one("img")]
    prefixes = Counter()
    for a in links:
        path = urlparse(urljoin(base, a["href"])).path
        prefixes[re.sub(r"\d+", "{n}", path)] += 1
    print("  링크 패턴 상위:", prefixes.most_common(8))

    # 이미지와 링크를 같이 가진 요소 중 가장 많이 반복되는 (태그, 클래스) = 카드일 가능성이 높다
    shapes = Counter()
    for el in soup.find_all(True):
        if el.select_one("a[href]") and el.select_one("img") and len(el.get_text(strip=True)) < 400:
            shapes[(el.name, " ".join(el.get("class", [])))] += 1
    print("  카드 후보 (태그, class) 상위:", shapes.most_common(5))
    for (tag, cls), n in shapes.most_common(2):
        if n < 5:
            continue
        el = soup.find(tag, class_=cls.split()[0]) if cls else soup.find(tag)
        if el:
            html = re.sub(r"\s+", " ", str(el))
            print(f"\n  --- 카드 예시 <{tag} class='{cls}'> x{n} ---\n  {html[:1800]}\n")
            print("  카드 텍스트:", el.get_text(" | ", strip=True)[:300])


def probe_static(url: str) -> None:
    print(f"\n===== [원본 HTML] {url}")
    resp = requests.get(url, headers=HEADERS, timeout=20)
    print("  status", resp.status_code, "| final", resp.url, "| bytes", len(resp.content),
          "| content-type", resp.headers.get("content-type"))
    soup = BeautifulSoup(resp.text, "html.parser")
    print("  <title>", soup.title.get_text(strip=True) if soup.title else None)
    print("  __NEXT_DATA__:", bool(soup.select_one("script#__NEXT_DATA__")),
          "| 스크립트 수:", len(soup.select("script")))
    api_hints = set(re.findall(r"""["'](/[\w/\-.]*(?:api|ajax|json|list)[\w/\-.?=&]*)["']""", resp.text))
    print("  스크립트 속 API 경로 후보:", sorted(api_hints)[:20])
    card_candidates(soup, resp.url)


def probe_rendered(url: str) -> None:
    from playwright.sync_api import sync_playwright

    print(f"\n===== [브라우저 렌더링] {url}")
    xhr: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.on(
            "response",
            lambda r: xhr.append(f"{r.request.method} {r.status} {r.url[:200]} [{r.headers.get('content-type', '')[:30]}]")
            if r.request.resource_type in ("xhr", "fetch") else None,
        )
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        before = len(page.content())
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(2500)
        print("  스크롤 후 HTML 증가:", len(page.content()) - before, "bytes (무한스크롤이면 크게 늘어남)")
        print("  XHR/fetch 요청:")
        for line in xhr[:25]:
            print("   ", line)
        card_candidates(BeautifulSoup(page.content(), "html.parser"), page.url)
        browser.close()


def probe_cards_detail(url: str, selector: str, n: int = 6) -> None:
    """카드 몇 개의 전체 HTML을 그대로 출력 — 앞·중간·끝에서 골라서 서로 다른 종류가 섞이는지 본다."""
    from playwright.sync_api import sync_playwright

    print(f"\n===== [카드 전체 HTML] {url} ({selector})")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(url, wait_until="networkidle", timeout=45000)
        for _ in range(4):
            page.mouse.wheel(0, 8000)
            page.wait_for_timeout(1500)
        cards = page.locator(selector)
        total = cards.count()
        print(f"  카드 {total}개. 인덱스 {[0, total // 4, total // 2, 3 * total // 4, total - 1]} 출력")
        for i in [0, total // 4, total // 2, 3 * total // 4, total - 1][:n]:
            html = re.sub(r"\s+", " ", cards.nth(i).inner_html())
            print(f"\n  --- 카드 #{i} ---\n  {html[:3500]}")
        # 사이트가 제공하는 분류/채널 탭(링크 텍스트와 주소)
        tabs = page.eval_on_selector_all(
            "a[href*='ct='], a[href*='type='], a[href*='ctype='], [data-ct], [data-type]",
            "els => els.map(e => (e.innerText||'').trim() + ' -> ' + (e.getAttribute('href')||e.dataset.ct||e.dataset.type||''))",
        )
        print("\n  분류/채널 탭 후보:", sorted(set(t for t in tabs if t.strip(" ->")))[:40])
        browser.close()


def probe_robots(url: str) -> None:
    root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    try:
        r = requests.get(root + "/robots.txt", headers=HEADERS, timeout=10)
        print(f"\n===== robots.txt ({r.status_code})\n{r.text[:800]}")
    except requests.RequestException as e:
        print("robots.txt 실패:", e)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--cards":  # python probe.py --cards <url> <css selector>
        probe_cards_detail(args[1], args[2])
        sys.exit(0)
    for target in args:
        for fn in (probe_robots, probe_static, probe_rendered):
            try:
                fn(target)
            except Exception as e:  # noqa: BLE001 - 조사용이라 단계별로 계속
                print(f"  {fn.__name__} 실패: {e}")
