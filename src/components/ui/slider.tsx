import { Slider as SliderPrimitive } from "@base-ui/react/slider"
import { cn } from "cn"

function Slider({
  className,
  ...props
}: SliderPrimitive.Root.Props<readonly number[]>) {
  return (
    <SliderPrimitive.Root data-slot="slider" className={cn("w-full", className)} {...props}>
      <SliderPrimitive.Control className="relative flex h-5 w-full items-center">
        <SliderPrimitive.Track className="h-1.5 w-full rounded-full bg-muted">
          <SliderPrimitive.Indicator className="h-full rounded-full bg-primary" />
          <SliderPrimitive.Thumb
            data-index="0"
            className="size-5 rounded-full border-2 border-primary bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <SliderPrimitive.Thumb
            data-index="1"
            className="size-5 rounded-full border-2 border-primary bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
        </SliderPrimitive.Track>
      </SliderPrimitive.Control>
    </SliderPrimitive.Root>
  )
}

export { Slider }
