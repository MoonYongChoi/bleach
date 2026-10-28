import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { type Campaign, dDay } from "@/lib/campaigns";

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

export function CampaignCard({ campaign }: { campaign: Campaign }) {
  const region = [campaign.region_sido, campaign.region_gugun].filter(Boolean).join(" ");

  return (
    <a
      href={campaign.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 rounded-2xl border border-border bg-card p-4 transition-colors hover:bg-muted/40"
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
          <Badge variant="secondary" className="font-normal text-muted-foreground">
            {campaign.platform}
          </Badge>
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
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          {region && <span>{region}</span>}
          {campaign.deadline_date && (
            <span>~{campaign.deadline_date.slice(5).replace("-", ".")} 모집</span>
          )}
        </div>
      </div>
    </a>
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
