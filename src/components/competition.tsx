import { applyRate, formatCompetition, type Campaign } from "@/lib/campaigns";
import { cn } from "cn";

type Tone = "calm" | "even" | "hot";

function toneFor(rate: number): Tone {
  if (rate < 1) return "calm";
  if (rate < 5) return "even";
  return "hot";
}

const TONE_STYLES: Record<Tone, { pill: string; fill: string; label: string }> = {
  calm: { pill: "bg-mint/10 text-mint", fill: "bg-mint", label: "여유" },
  even: { pill: "bg-primary/10 text-primary", fill: "bg-primary", label: "보통" },
  hot: { pill: "bg-coral/10 text-coral", fill: "bg-coral", label: "치열" },
};

// 게이지가 가득 차는 지점: 모집 1명당 6명 이상이면 꽉 참
const GAUGE_FULL_AT = 6;

/**
 * 경쟁률 한 줄: [3.2:1] ▮▮▮▯▯▯ 신청 32 / 모집 10명
 * 숫자는 디스플레이 글꼴로 크게, 게이지는 색으로 "여유/보통/치열"을 한눈에 보여준다.
 * 신청 인원을 모르면 모집 인원만 보여준다.
 */
export function Competition({ campaign }: { campaign: Pick<Campaign, "recruit_count" | "applicant_count"> }) {
  const rate = applyRate(campaign);
  const { recruit_count: recruit, applicant_count: applicant } = campaign;

  if (recruit === null || recruit === undefined) return null;
  if (rate === null) {
    return <p className="text-xs text-muted-foreground">모집 {recruit}명</p>;
  }

  const tone = toneFor(rate);
  const styles = TONE_STYLES[tone];
  const ratio = formatCompetition(rate);
  const fill = Math.max(0.06, Math.min(rate / GAUGE_FULL_AT, 1));

  return (
    <div
      className="flex items-center gap-2"
      role="img"
      aria-label={`경쟁 ${styles.label}, 모집 ${recruit}명에 신청 ${applicant}명`}
    >
      <span
        className={cn(
          "inline-flex h-6 min-w-12 items-center justify-center rounded-md px-1.5 font-display text-[13px] font-bold leading-none tabular-nums",
          styles.pill
        )}
      >
        {ratio}
      </span>
      <span className="relative h-1 w-10 shrink-0 overflow-hidden rounded-full bg-mist" aria-hidden>
        <span
          className={cn("gauge-fill absolute inset-0 rounded-full", styles.fill)}
          style={{ width: `${fill * 100}%` }}
        />
      </span>
      <span className="truncate text-xs tabular-nums text-muted-foreground">
        신청 {applicant} / 모집 {recruit}명
      </span>
    </div>
  );
}
