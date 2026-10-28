import { SearchXIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-muted">
        <SearchXIcon className="size-7 text-muted-foreground" />
      </div>
      <div>
        <p className="font-medium text-foreground">조건에 맞는 체험단이 없어요</p>
        <p className="mt-1 text-sm text-muted-foreground">
          다른 지역이나 카테고리로 다시 찾아보시겠어요?
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={onReset}>
          필터 초기화
        </Button>
        <Button onClick={onReset}>전체 체험단 보기</Button>
      </div>
    </div>
  );
}
