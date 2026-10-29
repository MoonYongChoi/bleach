import { StarIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type Campaign,
  CAMPAIGN_TYPE_LABELS,
  dDay,
  REVIEW_CHANNEL_LABELS,
} from "@/lib/campaigns";
import { cn } from "cn";

function DdayLabel({ deadlineDate }: { deadlineDate: string | null }) {
  if (!deadlineDate) {
    return <span className="text-sm font-semibold text-muted-foreground">상시모집</span>;
  }
  const d = dDay(deadlineDate)!;
  return (
    <span
      className={
        d <= 3
          ? "text-sm font-semibold text-destructive"
          : "text-sm font-semibold text-muted-foreground"
      }
    >
      {d <= 0 ? "D-day" : `D-${d}`}
    </span>
  );
}

export function CampaignCard({
  campaign,
  favorite,
  onToggleFavorite,
}: {
  campaign: Campaign;
  favorite: boolean;
  onToggleFavorite: () => void;
}) {
  const typeLabel = campaign.campaign_type ? CAMPAIGN_TYPE_LABELS[campaign.campaign_type]?.label : undefined;
  const region = [campaign.region_sido, campaign.region_gugun].filter(Boolean).join(" ");
  const channels = campaign.review_channels.map((c) => REVIEW_CHANNEL_LABELS[c] ?? c);
  const metaParts = [
    region || null,
    campaign.deadline_date ? `~${campaign.deadline_date.slice(5).replace("-", ".")} 모집` : null,
    campaign.recruit_count !== null
      ? `신청 ${campaign.applicant_count ?? "?"} / 모집 ${campaign.recruit_count}명`
      : null,
  ].filter(Boolean);

  return (
    <div className="relative flex rounded-2xl border border-border bg-card transition-colors hover:bg-muted/40">
      <a
        href={campaign.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-w-0 flex-1 gap-3 p-4 pr-1"
      >
        {campaign.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- external, per-domain CDN hosts; not worth next.config allowlisting yet
          <img
            src={campaign.image_url}
            alt=""
            className="size-16 shrink-0 rounded-xl object-cover"
          />
        ) : (
          <div className="size-16 shrink-0 rounded-xl bg-muted" />
        )}

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-1">
              <Badge variant="secondary" className="font-normal text-muted-foreground">
                {campaign.platform}
              </Badge>
              {typeLabel && (
                <Badge variant="outline" className="font-normal text-muted-foreground">
                  {typeLabel}
                </Badge>
              )}
            </div>
            <DdayLabel deadlineDate={campaign.deadline_date} />
          </div>
          {campaign.vendor && (
            <p className="line-clamp-1 text-xs font-medium text-foreground/70">{campaign.vendor}</p>
          )}
          <p className="line-clamp-2 text-[15px] font-medium leading-snug text-foreground">
            {campaign.title}
          </p>
          {campaign.description && (
            <p className="line-clamp-1 text-xs text-muted-foreground">{campaign.description}</p>
          )}
          <div className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
            {metaParts.map((part, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-border">·</span>}
                {part}
              </span>
            ))}
          </div>
          {channels.length > 0 && (
            <p className="text-xs font-medium text-primary">{channels.join(" · ")} 리뷰</p>
          )}
        </div>
      </a>

      <button
        onClick={onToggleFavorite}
        aria-pressed={favorite}
        aria-label={favorite ? "관심 해제" : "관심 체험단에 추가"}
        className="flex w-11 shrink-0 items-start justify-center pt-11 text-muted-foreground/60 hover:text-amber-500 focus-visible:outline-2 focus-visible:outline-ring"
      >
        <StarIcon className={cn("size-5", favorite && "fill-amber-400 text-amber-400")} />
      </button>
    </div>
  );
}

export function CampaignCardSkeleton() {
  return (
    <div className="flex gap-3 rounded-2xl border border-border bg-card p-4">
      <Skeleton className="size-16 shrink-0 rounded-xl" />
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-12 rounded-full" />
          <Skeleton className="h-4 w-8" />
        </div>
        <Skeleton className="h-5 w-4/5" />
        <Skeleton className="h-3.5 w-2/5" />
      </div>
    </div>
  );
}
