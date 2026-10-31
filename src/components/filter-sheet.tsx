"use client";

import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  CAMPAIGN_TYPE_LABELS,
  gugunKey,
  PLATFORMS,
  REVIEW_CHANNEL_LABELS,
  type ApplyRateRange,
  type FilterOptions,
  type SortOption,
} from "@/lib/campaigns";
import { cn } from "cn";

export type FilterSection = "type" | "region" | "category" | "channel" | "platform" | "applyRate";

export interface FilterState {
  types: string[];
  sidos: string[];
  /** "경기 하남시" 형태 — campaigns.ts gugunKey() */
  guguns: string[];
  categories: string[];
  channels: string[];
  platforms: string[];
  applyRate: ApplyRateRange | null;
  favoritesOnly: boolean;
  sort: SortOption;
  /** 마감임박순일 때 상시모집(마감일 없음)도 보여줄지 */
  includeOpenEnded: boolean;
}

export const EMPTY_FILTER_STATE: FilterState = {
  types: [],
  sidos: [],
  guguns: [],
  categories: [],
  channels: [],
  platforms: [],
  applyRate: null,
  favoritesOnly: false,
  sort: "deadline",
  includeOpenEnded: true,
};

/** 정렬·관심 보기를 뺀 "걸러내는 조건" 개수 — 필터 버튼 배지에 쓴다. */
export function activeFilterCount(f: FilterState) {
  return (
    f.types.length +
    f.sidos.length +
    f.guguns.length +
    f.categories.length +
    f.channels.length +
    f.platforms.length +
    (f.applyRate ? 1 : 0)
  );
}

/** 시트 안의 "초기화"는 정렬과 관심 보기는 건드리지 않는다 — 시트에서 고른 것만 지운다. */
function clearSheetFilters(f: FilterState): FilterState {
  return { ...EMPTY_FILTER_STATE, sort: f.sort, includeOpenEnded: f.includeOpenEnded, favoritesOnly: f.favoritesOnly };
}

// 경쟁률(신청 ÷ 모집) 슬라이더 범위: 0~10:1. 오른쪽 끝에 두면 "10:1 이상"까지 무제한으로 연다.
const APPLY_RATE_SLIDER_MAX = 10;
const APPLY_RATE_PRESETS: { label: string; range: ApplyRateRange }[] = [
  { label: "여유 (1:1 미만)", range: { min: 0, max: 1 } },
  { label: "보통 (1~5:1)", range: { min: 1, max: 5 } },
  { label: "치열 (5:1 이상)", range: { min: 5, max: Infinity } },
];

function scrollToSection(id: FilterSection, behavior: ScrollBehavior) {
  document.getElementById(`filter-section-${id}`)?.scrollIntoView({ behavior, block: "start" });
}

function formatRange(min: number, max: number) {
  const n = (v: number) => Math.round(v * 10) / 10;
  if (min <= 0 && max >= APPLY_RATE_SLIDER_MAX) return "전체";
  if (min <= 0) return `${n(max)}:1 이하`;
  if (max >= APPLY_RATE_SLIDER_MAX) return `${n(min)}:1 이상`;
  return `${n(min)}~${n(max)}:1`;
}

const SECTION_TITLES: Record<FilterSection, string> = {
  type: "체험 방식",
  region: "지역",
  category: "카테고리",
  channel: "리뷰 채널",
  platform: "체험단 사이트",
  applyRate: "경쟁률",
};

export function FilterSheet({
  open,
  onOpenChange,
  initialSection,
  options,
  value,
  onApply,
  countFor,
  onRequestPlatform,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialSection: FilterSection;
  options: FilterOptions;
  value: FilterState;
  onApply: (next: FilterState) => void;
  /** 지금 고른 조건으로 몇 개가 나오는지 — 적용 버튼에 미리 보여준다 */
  countFor: (draft: FilterState) => Promise<number>;
  onRequestPlatform: () => void;
}) {
  const [draft, setDraft] = useState<FilterState>(value);
  const [count, setCount] = useState<number | null>(null);

  // `open` is driven externally (quick-filter chips set it directly), so the
  // underlying dialog's onOpenChange never fires for that transition — sync here instead.
  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: reset the draft each time the sheet (re)opens
    setDraft(value);
    // 누른 칩에 해당하는 섹션으로 바로 이동 (시트 열림 애니메이션 다음 프레임)
    const t = setTimeout(() => scrollToSection(initialSection, "auto"), 50);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-sync on open/section change, not every `value` edit
  }, [open, initialSection]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const t = setTimeout(() => {
      countFor(draft)
        .then((n) => !cancelled && setCount(n))
        .catch(() => !cancelled && setCount(null));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [open, draft, countFor]);

  function toggle(key: "types" | "sidos" | "categories" | "channels" | "platforms", item: string) {
    setDraft((d) => {
      const list = d[key];
      return { ...d, [key]: list.includes(item) ? list.filter((v) => v !== item) : [...list, item] };
    });
  }

  const sliderValue: [number, number] = draft.applyRate
    ? [draft.applyRate.min, Math.min(draft.applyRate.max, APPLY_RATE_SLIDER_MAX)]
    : [0, APPLY_RATE_SLIDER_MAX];

  const sections: FilterSection[] = [
    "type",
    "region",
    "category",
    ...(options.channels.length > 0 ? (["channel"] as const) : []),
    "platform",
    "applyRate",
  ];

  const selectedCount: Record<FilterSection, number> = {
    type: draft.types.length,
    region: draft.sidos.length + draft.guguns.length,
    category: draft.categories.length,
    channel: draft.channels.length,
    platform: draft.platforms.length,
    applyRate: draft.applyRate ? 1 : 0,
  };

  const sectionProps = (id: FilterSection) => ({
    id,
    selected: selectedCount[id],
    onClear: () => clearSection(id),
  });

  function clearSection(section: FilterSection) {
    setDraft((d) => {
      switch (section) {
        case "type":
          return { ...d, types: [] };
        case "region":
          return { ...d, sidos: [], guguns: [] };
        case "category":
          return { ...d, categories: [] };
        case "channel":
          return { ...d, channels: [] };
        case "platform":
          return { ...d, platforms: [] };
        case "applyRate":
          return { ...d, applyRate: null };
      }
    });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="mx-auto max-h-[85dvh] max-w-md gap-0 rounded-t-2xl">
        <SheetHeader className="shrink-0 pb-2">
          <SheetTitle>필터</SheetTitle>
        </SheetHeader>

        {/* 섹션 바로가기 — 선택이 있는 섹션은 개수로 표시 */}
        <nav className="flex shrink-0 gap-1.5 overflow-x-auto border-b border-border px-4 pb-3" aria-label="필터 항목">
          {sections.map((id) => (
            <button
              key={id}
              onClick={() => scrollToSection(id, "smooth")}
              className={cn(
                "flex shrink-0 items-center gap-1 rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground",
                selectedCount[id] > 0 && "bg-primary/10 text-primary"
              )}
            >
              {SECTION_TITLES[id]}
              {selectedCount[id] > 0 && <span className="tabular-nums">{selectedCount[id]}</span>}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-y-auto px-4">
          <Section {...sectionProps("type")} hint="무엇을 하게 되나요?">
            <div className="grid grid-cols-2 gap-2">
              {options.types.map((type) => (
                <OptionCard
                  key={type}
                  active={draft.types.includes(type)}
                  onClick={() => toggle("types", type)}
                  label={CAMPAIGN_TYPE_LABELS[type]?.label ?? type}
                  hint={CAMPAIGN_TYPE_LABELS[type]?.hint}
                />
              ))}
            </div>
          </Section>

          <Section {...sectionProps("region")} hint="방문 체험만 해당">
            <RegionPicker
              sidos={options.sidos}
              guguns={options.guguns}
              selectedSidos={draft.sidos}
              selectedGuguns={draft.guguns}
              onChange={(sidos, guguns) => setDraft((d) => ({ ...d, sidos, guguns }))}
            />
          </Section>

          <Section {...sectionProps("category")}>
            <ChipGroup>
              {options.categories.map((category) => (
                <Chip
                  key={category}
                  active={draft.categories.includes(category)}
                  onClick={() => toggle("categories", category)}
                >
                  {category}
                </Chip>
              ))}
            </ChipGroup>
          </Section>

          {options.channels.length > 0 && (
            <Section {...sectionProps("channel")} hint="어디에 리뷰를 올리나요?">
              <ChipGroup>
                {options.channels.map((channel) => (
                  <Chip
                    key={channel}
                    active={draft.channels.includes(channel)}
                    onClick={() => toggle("channels", channel)}
                  >
                    {REVIEW_CHANNEL_LABELS[channel] ?? channel}
                  </Chip>
                ))}
              </ChipGroup>
            </Section>
          )}

          <Section {...sectionProps("platform")}>
            <ChipGroup>
              {PLATFORMS.map((platform) => (
                <Chip
                  key={platform}
                  active={draft.platforms.includes(platform)}
                  onClick={() => toggle("platforms", platform)}
                >
                  {platform}
                </Chip>
              ))}
            </ChipGroup>
            <button
              onClick={onRequestPlatform}
              className="mt-3 text-xs text-muted-foreground underline underline-offset-2"
            >
              다른 사이트도 모아주세요 →
            </button>
          </Section>

          <Section {...sectionProps("applyRate")} hint="모집 1명당 신청자 수">
            <div className="flex flex-col gap-4">
              <ChipGroup>
                {APPLY_RATE_PRESETS.map((preset) => {
                  const active =
                    draft.applyRate?.min === preset.range.min && draft.applyRate?.max === preset.range.max;
                  return (
                    <Chip
                      key={preset.label}
                      active={active}
                      onClick={() => setDraft((d) => ({ ...d, applyRate: active ? null : preset.range }))}
                    >
                      {preset.label}
                    </Chip>
                  );
                })}
              </ChipGroup>
              <div className="flex flex-col gap-3 rounded-xl bg-muted/60 p-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>직접 범위 지정</span>
                  <span className="text-sm font-semibold tabular-nums text-foreground">
                    {formatRange(sliderValue[0], sliderValue[1])}
                  </span>
                </div>
                <Slider
                  min={0}
                  max={APPLY_RATE_SLIDER_MAX}
                  step={0.5}
                  minStepsBetweenValues={1}
                  value={sliderValue}
                  onValueChange={(next) => {
                    const [min, max] = next as number[];
                    setDraft((d) => ({
                      ...d,
                      applyRate: { min, max: max >= APPLY_RATE_SLIDER_MAX ? Infinity : max },
                    }));
                  }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                신청 현황을 공개하는 체험단만 이 조건으로 걸러집니다.
              </p>
            </div>
          </Section>
        </div>

        <div className="flex gap-2 border-t border-border bg-popover px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <Button variant="outline" className="w-24" onClick={() => setDraft(clearSheetFilters)}>
            초기화
          </Button>
          <Button
            className="flex-1"
            disabled={count === 0}
            onClick={() => {
              onApply(draft);
              onOpenChange(false);
            }}
          >
            {count === null ? "결과 보기" : count === 0 ? "조건에 맞는 체험단 없음" : `${count.toLocaleString()}개 결과 보기`}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Section({
  id,
  hint,
  selected,
  onClear,
  children,
}: {
  id: FilterSection;
  hint?: string;
  selected: number;
  onClear: () => void;
  children: React.ReactNode;
}) {
  return (
    <section
      id={`filter-section-${id}`}
      className="scroll-mt-2 border-b border-border py-4 last:border-b-0"
      aria-labelledby={`filter-${id}`}
    >
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h3 id={`filter-${id}`} className="text-sm font-semibold text-foreground">
          {SECTION_TITLES[id]}
          {hint && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{hint}</span>}
        </h3>
        {selected > 0 && (
          <button onClick={onClear} className="text-xs text-muted-foreground underline-offset-2 hover:underline">
            선택 해제
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

/**
 * 시/도를 누르면 그 아래 시/군/구가 펼쳐진다. "경기 전체"와 개별 시/군/구는 서로 배타적:
 * 하위 지역을 고르면 "전체"가 풀리고, "전체"를 고르면 그 시/도의 하위 선택이 지워진다.
 */
function RegionPicker({
  sidos,
  guguns,
  selectedSidos,
  selectedGuguns,
  onChange,
}: {
  sidos: string[];
  guguns: FilterOptions["guguns"];
  selectedSidos: string[];
  selectedGuguns: string[];
  onChange: (sidos: string[], guguns: string[]) => void;
}) {
  const firstSelected = selectedSidos[0] ?? selectedGuguns[0]?.split(" ")[0] ?? null;
  const [expanded, setExpanded] = useState<string | null>(firstSelected);

  const pickedIn = (sido: string) => selectedGuguns.filter((k) => k.startsWith(`${sido} `)).length;
  const subOptions = expanded ? guguns[expanded] ?? [] : [];
  const wholeSelected = expanded ? selectedSidos.includes(expanded) : false;

  function toggleWhole(sido: string) {
    if (selectedSidos.includes(sido)) {
      onChange(selectedSidos.filter((s) => s !== sido), selectedGuguns);
    } else {
      onChange([...selectedSidos, sido], selectedGuguns.filter((k) => !k.startsWith(`${sido} `)));
    }
  }

  function toggleGugun(sido: string, gugun: string) {
    const key = gugunKey(sido, gugun);
    const next = selectedGuguns.includes(key)
      ? selectedGuguns.filter((k) => k !== key)
      : [...selectedGuguns, key];
    onChange(selectedSidos.filter((s) => s !== sido), next);
  }

  return (
    <div className="flex flex-col gap-3">
      <ChipGroup>
        {sidos.map((sido) => {
          const picked = pickedIn(sido);
          const whole = selectedSidos.includes(sido);
          const hasSub = (guguns[sido]?.length ?? 0) > 0;
          return (
            <Chip
              key={sido}
              active={whole || picked > 0}
              onClick={() => (hasSub ? setExpanded(expanded === sido ? null : sido) : toggleWhole(sido))}
            >
              {sido}
              {picked > 0 && <span className="ml-1 tabular-nums">{picked}</span>}
              {hasSub && <span className="ml-0.5 text-[10px]">{expanded === sido ? "▴" : "▾"}</span>}
            </Chip>
          );
        })}
      </ChipGroup>

      {expanded && subOptions.length > 0 && (
        <div className="flex flex-col gap-2 rounded-xl bg-muted/60 p-3">
          <p className="text-xs font-medium text-muted-foreground">{expanded} 하위 지역</p>
          <div className="flex flex-wrap gap-1.5">
            <Chip small active={wholeSelected} onClick={() => toggleWhole(expanded)}>
              {expanded} 전체
            </Chip>
            {subOptions.map(({ name, count }) => (
              <Chip
                key={name}
                small
                active={selectedGuguns.includes(gugunKey(expanded, name))}
                onClick={() => toggleGugun(expanded, name)}
              >
                {name.replace(/(시|군|구)$/, "")}
                <span className="ml-1 text-[11px] tabular-nums opacity-60">{count}</span>
              </Chip>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ChipGroup({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap gap-2">{children}</div>;
}

function Chip({
  active,
  small,
  onClick,
  children,
}: {
  active: boolean;
  small?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex items-center rounded-full border border-border bg-card text-foreground transition-[background-color,border-color,color,transform] duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:scale-95",
        small ? "px-3 py-1 text-[13px]" : "px-3.5 py-1.5 text-sm",
        active && "border-primary bg-primary/10 font-medium text-primary"
      )}
    >
      {children}
    </button>
  );
}

function OptionCard({
  active,
  onClick,
  label,
  hint,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  hint?: string;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex flex-col items-start gap-0.5 rounded-xl border border-border px-3 py-2.5 text-left transition-[background-color,border-color,transform] duration-200 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
        active && "border-primary bg-primary/10"
      )}
    >
      <span className={cn("text-sm font-medium text-foreground", active && "text-primary")}>{label}</span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </button>
  );
}
