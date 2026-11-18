import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-semibold whitespace-nowrap transition-[background,color,box-shadow,transform] duration-150 active:translate-y-px disabled:pointer-events-none disabled:opacity-55 cursor-pointer",
  {
    variants: {
      variant: {
        primary: "bg-turmeric text-night hover:bg-[#ffc955] shadow-[0_6px_0_-2px_#d9961a] hover:shadow-[0_8px_0_-2px_#d9961a] active:shadow-[0_3px_0_-1px_#d9961a]",
        dark: "bg-night text-jasmine hover:bg-night-3",
        outline: "border-2 border-ink/15 bg-white text-ink hover:border-ink/40",
        outlineDark: "border-2 border-white/20 text-jasmine hover:border-white/50 hover:bg-white/5",
        ghost: "text-ink-soft hover:text-ink hover:bg-jasmine-2",
        ghostDark: "text-mist hover:text-white hover:bg-white/8",
        leaf: "bg-leaf text-white hover:bg-[#239d62]",
      },
      size: {
        sm: "h-9 px-3.5 text-sm rounded-[10px]",
        md: "h-11 px-5 text-[0.95rem] rounded-[12px]",
        lg: "h-14 px-7 text-[1.05rem] rounded-[14px]",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => (
  <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
));
Button.displayName = "Button";

// eslint-disable-next-line react-refresh/only-export-components
export { buttonVariants };
