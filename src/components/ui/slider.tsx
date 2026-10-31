import { Slider as SliderPrimitive } from "@base-ui/react/slider"
import { cn } from "cn"

function Slider({
  className,
  ...props
}: SliderPrimitive.Root.Props<readonly number[]>) {
  return (
    <SliderPrimitive.Root data-slot="slider" className={cn("w-full", className)} {...props}>
      <SliderPrimitive.Control className="relative flex h-6 w-full items-center">
        <SliderPrimitive.Track className="h-1.5 w-full rounded-full bg-border">
          <SliderPrimitive.Indicator className="h-full rounded-full bg-primary" />
          <SliderPrimitive.Thumb
            data-index="0"
            className="size-6 rounded-full border-2 border-primary bg-card shadow-md transition-transform duration-150 data-dragging:scale-125 active:scale-125 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25"
          />
          <SliderPrimitive.Thumb
            data-index="1"
            className="size-6 rounded-full border-2 border-primary bg-card shadow-md transition-transform duration-150 data-dragging:scale-125 active:scale-125 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/25"
          />
        </SliderPrimitive.Track>
      </SliderPrimitive.Control>
    </SliderPrimitive.Root>
  )
}

export { Slider }
