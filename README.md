This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## 광고 (Google AdSense)

코드는 `src/lib/ads.ts`, `src/components/ad-slot.tsx`, `src/components/adsense-script.tsx`.

| 상태 | 조건 | 나오는 것 |
|---|---|---|
| 연결 | 게시자 ID(기본값 `ca-pub-2018630083097143`)가 올바름 | `<head>`의 AdSense 코드 |
| 목록 광고 | 위 + 광고 단위 ID(기본값 피드 내 광고 `1293649683`, layout key `-fi+6j-17-cv+rc`) | 캠페인 8개마다 광고 한 칸, 최대 6칸 |

광고 단위 ID가 없으면 목록에는 광고 칸이 생기지 않는다. 켜는 순서:

1. AdSense에서 사이트 연결·소유 확인 (확인 방법은 "애드센스 코드 스니펫". `<head>` 코드는 이미 나온다). `/ads.txt`는 넣지 않았다. AdSense가 요구하면 `google.com, pub-2018630083097143, DIRECT, f08c47fec0942fa0` 한 줄짜리 경로를 다시 만든다.
2. AdSense → 광고 → 광고 단위 → **피드 내 광고**를 만들고, 광고 단위 ID(숫자)를 Vercel 환경변수 `NEXT_PUBLIC_ADSENSE_SLOT`에 넣고 다시 배포한다. 피드형의 layout key가 있으면 `NEXT_PUBLIC_ADSENSE_LAYOUT_KEY`에도 넣는다.
3. AdSense의 "자동 광고"를 켜 두면 코드가 넣은 칸과 별개로 광고가 추가로 붙는다. 목록 UX를 직접 관리하려면 자동 광고는 끈다.

켜기 전에 확인할 것:

- **호스팅 약관**: Vercel Hobby(무료)는 비상업적 사용만 허용한다. 광고 수익을 쓰려면 Pro 등 상업적 사용이 가능한 플랜이 필요하다.
- **도메인**: 본인 소유 도메인이 있어야 AdSense 승인이 쉽다.
- **개인정보처리방침**: 광고 쿠키 사용을 알리는 페이지가 필요하다. 아직 없다.
- **콘텐츠 정책**: 다른 사이트의 정보를 모아 보여 주는 서비스는 "가치가 낮은 콘텐츠"로 거절될 수 있다.
- **수집 대상 사이트의 약관·robots**: 수익이 생기면 법적 위험이 달라진다.

광고는 캠페인이 있는 목록 안에만 들어가고, 로딩·오류·결과 없음 화면에는 넣지 않는다 (AdSense 정책).

## 관리 페이지 (/admin)

수집 현황(플랫폼별 상태, 수집 회차별 결과, 새 캠페인이 들어온 시각)을 보는 페이지. Basic 인증으로 막혀 있다.

- Vercel 환경변수 `ADMIN_PASSWORD`(필수), `ADMIN_USER`(선택, 기본 `admin`)
- `ADMIN_PASSWORD`가 없으면 /admin은 404
- 수집 회차 기록은 `scraper/run_all.py`가 `scrape_runs` 테이블에 남긴다 (`supabase/migrations/20261105_scrape_runs.sql`)

## 서울오빠 수집 (가정용 PC)

서울오빠는 데이터센터 IP(GitHub Actions, Vercel 서울 리전)의 접속을 막아 정기 수집에서 빠져 있다 (`local_only`).
집·사무실 PC에서 따로 돌린다.

```bash
git clone https://github.com/MoonYongChoi/bleach.git && cd bleach/scraper
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 저장소 루트의 .env.local 에 DATABASE_URL=... (Supabase → Connect → Session pooler 주소)
python run_all.py --only seoulouba --dry-run   # 수집·정제만, DB에 안 씀
python run_all.py --only seoulouba             # 적재 (/admin 수집 회차에 기록됨)
python reaper.py --only seoulouba --apply      # 목록에서 빠진 캠페인 종료 처리
```

하루 몇 번 돌리려면 cron(Mac/Linux) 또는 작업 스케줄러(Windows)에 위 적재 명령을 등록한다.
