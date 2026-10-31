import { cn } from "cn"

// 자리만 잡는 면 위로 옅은 빛이 한 번씩 지나간다 (prefers-reduced-motion이면 멈춘 면)
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("shimmer rounded-md bg-muted", className)}
      {...props}
    />
  )
}

export { Skeleton }
