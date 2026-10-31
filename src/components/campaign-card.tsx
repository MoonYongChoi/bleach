"use client";

import { useState } from "react";
import { StarIcon } from "lucide-react";
import { Competition } from "@/components/competition";
import { Skeleton } from "@/components/ui/skeleton";
import { Thumbnail } from "@/components/thumbnail";
import {
  type Campaign,
  CAMPAIGN_TYPE_LABELS,
  dDay,
  REVIEW_CHANNEL_LABELS,
} from "@/lib/campaigns";
import { cn } from "cn";

/** 썸네일 왼쪽 아래에 얹는 마감 표시. 3일 이하는 코랄로 눈에 띄게. */
function DeadlineTag({ deadlineDate }: { deadlineDate: string | null }) {
  if (!deadlineDate) {
    return (
      <span className="rounded-md bg-foreground/70 px-1.5 py-0.5 text-[11px] font-semibold text-white backdrop-blur-sm">
        상시
      </span>
    );
  }
  const d = dDay(deadlineDate)!;
  return (
    <span
      className={cn(
        "rounded-md px-1.5 py-0.5 font-display text-[12px] font-bold leading-none tabular-nums text-white",
        d <= 3 ? "bg-coral" : "bg-foreground/75 backdrop-blur-sm"
      )}
    >
      {d <= 0 ? "D-day" : `D-${d}`}
    </span>
  );
}

export function CampaignCard({
  campaign,
  favorite,
  onToggleFavorite,
  index,
  intro,
}: {
  campaign: Campaign;
  favorite: boolean;
  onToggleFavorite: () => void;
  /** 목록에서의 순서 — 첫 화면 등장 애니메이션 간격에만 쓴다 */
  index: number;
  /** 처음 한 번만 순서대로 올라오게 할지 */
  intro: boolean;
}) {
  const typeLabel = campaign.campaign_type ? CAMPAIGN_TYPE_LABELS[campaign.campaign_type]?.label : undefined;
  const region = [campaign.region_sido, campaign.region_gugun].filter(Boolean).join(" ");
  const channels = campaign.review_channels.map((c) => REVIEW_CHANNEL_LABELS[c] ?? c);
  const deadline = campaign.deadline_date ? `${campaign.deadline_date.slice(5).replace("-", ".")}까지` : null;

  // 별을 누른 순간에만 한 번 튀게 한다 (처음 그려질 때나 목록이 바뀔 때는 움직이지 않음)
  const [popKey, setPopKey] = useState(0);

  return (
    <li
      className={cn("relative flex", intro && index < 8 && "row-rise")}
      style={intro ? ({ "--i": index } as React.CSSProperties) : undefined}
    >
      <a
        href={campaign.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-w-0 flex-1 gap-3 px-4 py-3.5 pr-11 min-[360px]:gap-3.5 min-[360px]:pr-12 transition-colors duration-150 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring active:bg-muted/70 [@media(hover:hover)]:hover:bg-muted/50"
      >
        <div className="relative shrink-0 self-start">
          <Thumbnail key={campaign.image_url ?? campaign.id} src={campaign.image_url} category={campaign.category} />
          <div className="absolute bottom-1 left-1">
            <DeadlineTag deadlineDate={campaign.deadline_date} />
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          {/* 좁은 화면에서 이름이 세로로 꺾이지 않게 이름·유형은 한 덩어리로 두고, 채널은 모자라면 아래 줄로 내려간다 */}
          <p className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground">
            <span className="shrink-0 whitespace-nowrap font-medium text-foreground/80">{campaign.platform}</span>
            {typeLabel && (
              <span className="shrink-0 whitespace-nowrap rounded bg-muted px-1.5 py-px text-[11px] font-medium">{typeLabel}</span>
            )}
            {channels.length > 0 && <span className="text-primary">{channels.join("·")} 리뷰</span>}
          </p>
          <p className="line-clamp-2 text-[15px] font-semibold leading-snug tracking-tight text-foreground">
            {campaign.vendor ? <span className="font-medium text-foreground/60">{campaign.vendor} </span> : null}
            {campaign.title}
          </p>
          {(region || deadline) && (
            <p className="flex min-w-0 items-baseline gap-1 text-xs text-muted-foreground">
              {region && <span className="truncate">{region}</span>}
              {/* 마감일은 지역이 길어도 잘리지 않게 고정 */}
              {deadline && <span className="shrink-0 whitespace-nowrap">{region ? "· " : ""}{deadline}</span>}
            </p>
          )}
          <Competition campaign={campaign} />
        </div>
      </a>

      <button
        onClick={() => {
          if (!favorite) setPopKey((k) => k + 1);
          onToggleFavorite();
        }}
        aria-pressed={favorite}
        aria-label={favorite ? "관심 해제" : "관심 체험단에 추가"}
        className="absolute right-1 top-2 flex size-11 items-center justify-center text-muted-foreground/50 transition-colors hover:text-sun focus-visible:outline-2 focus-visible:outline-ring"
      >
        <StarIcon
          key={popKey}
          className={cn("size-5 transition-colors", favorite && "star-pop fill-sun text-sun")}
        />
      </button>
    </li>
  );
}

export function CampaignCardSkeleton() {
  return (
    <li className="flex gap-3.5 px-4 py-3.5" aria-hidden>
      <Skeleton className="size-[72px] shrink-0 rounded-2xl" />
      <div className="flex flex-1 flex-col gap-2 pt-0.5">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-3.5 w-2/5" />
        <Skeleton className="h-5 w-3/5" />
      </div>
    </li>
  );
}
