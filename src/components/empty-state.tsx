import { SearchXIcon, StarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({
  onReset,
  variant = "results",
}: {
  onReset: () => void;
  variant?: "results" | "favorites";
}) {
  if (variant === "favorites") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-muted">
          <StarIcon className="size-7 text-muted-foreground" />
        </div>
        <div>
          <p className="font-medium text-foreground">아직 관심 체험단이 없어요</p>
          <p className="mt-1 text-sm text-muted-foreground">
            목록에서 별을 누르면 여기에 모아 볼 수 있어요. 이 기기에만 저장됩니다.
          </p>
        </div>
        <Button onClick={onReset}>전체 체험단 보기</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-muted">
        <SearchXIcon className="size-7 text-muted-foreground" />
      </div>
      <div>
        <p className="font-medium text-foreground">조건에 맞는 체험단이 없어요</p>
        <p className="mt-1 text-sm text-muted-foreground">
          조건을 줄이거나 다른 지역·카테고리로 찾아보세요.
        </p>
      </div>
      <Button onClick={onReset}>조건 지우기</Button>
    </div>
  );
}
