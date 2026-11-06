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


def probe_scroll(url: str, selector: str, scrolls: int = 30, login_key: str | None = None) -> None:
    """무한스크롤 목록 조사: 스크롤마다 카드 수와 XHR(POST 본문 포함)을 찍고, 언제 멈추는지 본다.
    같은 사이트 첫 화면을 먼저 열어 봇 확인 쿠키를 받는다."""
    from playwright.sync_api import sync_playwright

    print(f"\n===== [무한스크롤 조사] {url} ({selector})")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if login_key:  # 로그인이 필요한 목록 (예: revu) — 커넥터의 로그인 절차를 그대로 쓴다
            from connectors import BY_KEY

            BY_KEY[login_key].prepare_browser(context)
        else:
            warm = context.new_page()
            warm.goto(base, wait_until="networkidle", timeout=45000)
            warm.close()
        page = context.new_page()
        log: list[str] = []

        def on_response(r):
            if r.request.resource_type not in ("xhr", "fetch"):
                return
            if re.search(r"google|doubleclick|adtraffic|facebook|kakao|naver\.com|analytics|clarity|hotjar", r.url):
                return
            body = r.request.post_data or ""
            try:
                text = r.text()
            except Exception:  # noqa: BLE001
                text = ""
            head = re.sub(r"\s+", " ", text[:300])
            log.append(f"{r.request.method} {r.status} {r.url[:160]} body={body[:400]!r} "
                       f"resp={len(text)}B cards~{text.count('c_box')} head={head!r}")

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(1500)
        print("  처음 카드:", page.locator(selector).count())
        stuck = 0
        for i in range(scrolls):
            before = page.locator(selector).count()
            page.mouse.wheel(0, 6000)
            page.wait_for_timeout(2500)
            page.keyboard.press("End")
            page.wait_for_timeout(1500)
            after = page.locator(selector).count()
            print(f"  스크롤 {i + 1}: {before} -> {after}")
            stuck = stuck + 1 if after == before else 0
            if stuck >= 3:
                print("  3번 연속 그대로라 멈춤")
                break
        cards = page.locator(selector)
        total = cards.count()
        for i in sorted({0, total // 2, max(total - 1, 0)}):
            if total:
                print(f"  카드 #{i} 글자:", re.sub(r"\s+", " ", cards.nth(i).inner_text())[:200])
        print("  XHR/fetch 요청 (처음 12개 + 마지막 4개):")
        for line in log[:12] + (["   ..."] if len(log) > 16 else []) + log[-4:]:
            print("   ", line[:900])
        # 목록 아래쪽 '더보기'·페이지 버튼, 분류 탭
        tail = page.eval_on_selector_all(
            "a, button",
            "els => els.map(e => (e.innerText||'').trim().slice(0,20) + ' -> ' + (e.getAttribute('href')||e.getAttribute('onclick')||'')).filter(t => /더보기|more|다음|page|cate|ca_id|ct=|sort|분류|전체/i.test(t))",
        )
        print("  더보기/분류/정렬 후보:", sorted(set(tail))[:60])
        print("  현재 주소:", page.url)
        browser.close()


def probe_text(url: str) -> None:
    """상세 페이지의 보이는 글자를 줄 단위로 그대로 출력 — 날짜·인원이 어떤 문장으로 적혀 있는지 본다."""
    print(f"\n===== [페이지 글자] {url}")
    resp = requests.get(url, headers=HEADERS, timeout=20)
    print(f"  status {resp.status_code} | bytes {len(resp.content)}")
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    lines = [ln for ln in soup.get_text("\n", strip=True).split("\n") if ln]
    print(f"  줄 수 {len(lines)} — 처음 70줄:")
    for i, ln in enumerate(lines[:70]):
        print(f"  {i:3d} | {ln[:140]}")
    # 날짜/기간처럼 보이는 줄만 따로
    dated = [ln for ln in lines if re.search(r"\d{1,2}\s*[./월]\s*\d{1,2}|기간|마감|D-\d", ln)]
    print("  날짜·기간 후보 줄:", dated[:15])


def probe_robots(url: str) -> None:
    root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    try:
        r = requests.get(root + "/robots.txt", headers=HEADERS, timeout=10)
        print(f"\n===== robots.txt ({r.status_code})\n{r.text[:800]}")
    except requests.RequestException as e:
        print("robots.txt 실패:", e)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--text":  # python probe.py --text <url> [<url> ...]
        for target in args[1:]:
            probe_text(target)
        sys.exit(0)
    if args and args[0] == "--scroll":  # python probe.py --scroll <url> <css selector> [스크롤 횟수]
        probe_scroll(args[1], args[2], int(args[3]) if len(args) > 3 else 30, args[4] if len(args) > 4 else None)
        sys.exit(0)
    if args and args[0] == "--cards":  # python probe.py --cards <url> <css selector>
        probe_cards_detail(args[1], args[2])
        sys.exit(0)
    for target in args:
        for fn in (probe_robots, probe_static, probe_rendered):
            try:
                fn(target)
            except Exception as e:  # noqa: BLE001 - 조사용이라 단계별로 계속
                print(f"  {fn.__name__} 실패: {e}")
