import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-[#E07A5F]/30 focus-visible:ring-[3px]",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-[#E07A5F] to-[#D4583D] text-white hover:from-[#D4583D] hover:to-[#C04830] shadow-md shadow-[#E07A5F]/20",
        destructive:
          "bg-[#D64545] text-white hover:bg-[#C03A3A] focus-visible:ring-red-200",
        outline:
          "border-2 border-[#E8E0D8] bg-white shadow-sm hover:bg-[#F5F0EB] hover:text-[#1A1814] text-[#5C5549]",
        secondary:
          "bg-[#F5F0EB] text-[#5C5549] hover:bg-[#E8E0D8]",
        ghost:
          "hover:bg-[#F5F0EB] hover:text-[#1A1814] text-[#5C5549]",
        link: "text-[#E07A5F] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-8 rounded-lg gap-1.5 px-3",
        lg: "h-12 rounded-xl px-8",
        icon: "size-10",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
