import { Badge } from "@/components/ui/badge";

export function BottomBanner() {
  return (
    <div className="flex h-[50px] shrink-0 items-center justify-center gap-2 border-t border-border bg-muted/40">
      <Badge variant="outline" className="text-muted-foreground">
        AD
      </Badge>
      <span className="text-xs text-muted-foreground">하단 고정 배너 영역 (320×50)</span>
    </div>
  );
}
