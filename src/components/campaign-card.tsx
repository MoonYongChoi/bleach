import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { type Campaign, dDay } from "@/lib/campaigns";

export function CampaignCard({ campaign }: { campaign: Campaign }) {
  const d = dDay(campaign.deadline_date);
  const region = [campaign.region_sido, campaign.region_gugun].filter(Boolean).join(" ");

  return (
    <a
      href={campaign.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col gap-2 rounded-2xl border border-border bg-card p-4 transition-colors hover:bg-muted/40"
    >
      <div className="flex items-center justify-between">
        <Badge variant="secondary" className="font-normal text-muted-foreground">
          {campaign.platform}
        </Badge>
        {d !== null && (
          <span
            className={
              d <= 3
                ? "text-sm font-semibold text-destructive"
                : "text-sm font-semibold text-muted-foreground"
            }
          >
            {d <= 0 ? "D-day" : `D-${d}`}
          </span>
        )}
      </div>
      <p className="text-[15px] font-medium leading-snug text-foreground">{campaign.title}</p>
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {region && <span>{region}</span>}
        {campaign.deadline_date && (
          <span>~{campaign.deadline_date.slice(5).replace("-", ".")} 모집</span>
        )}
      </div>
    </a>
  );
}

export function AdCard() {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-card p-4">
      <div className="h-10 w-10 shrink-0 rounded-lg bg-muted" />
      <div className="flex-1">
        <p className="text-[15px] font-medium text-foreground">스폰서 체험단 모집 안내</p>
        <p className="text-xs text-muted-foreground">카카오 애드핏 · 광고</p>
      </div>
      <Badge variant="outline" className="text-muted-foreground">
        AD
      </Badge>
    </div>
  );
}

export function CampaignCardSkeleton() {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-12 rounded-full" />
        <Skeleton className="h-4 w-8" />
      </div>
      <Skeleton className="h-5 w-4/5" />
      <Skeleton className="h-3.5 w-2/5" />
    </div>
  );
}
