import { CloudOffIcon, SearchXIcon, StarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({
  onReset,
  variant = "results",
}: {
  onReset: () => void;
  variant?: "results" | "favorites" | "error";
}) {
  if (variant === "error") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center" role="alert">
        <div className="flex size-16 items-center justify-center rounded-full bg-coral/10">
          <CloudOffIcon className="size-7 text-coral" />
        </div>
        <div>
          <p className="font-medium text-foreground">체험단 목록을 불러오지 못했어요</p>
          <p className="mt-1 text-sm text-muted-foreground">
            네트워크 연결을 확인하고 다시 시도해 주세요. 계속 안 되면 잠시 뒤에 다시 열어 보세요.
          </p>
        </div>
        <Button onClick={onReset}>다시 시도</Button>
      </div>
    );
  }

  if (variant === "favorites") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-primary/10">
          <StarIcon className="size-7 text-primary" />
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
      <div className="flex size-16 items-center justify-center rounded-full bg-primary/10">
        <SearchXIcon className="size-7 text-primary" />
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
