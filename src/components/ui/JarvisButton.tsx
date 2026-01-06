import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const jarvisButtonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-orbitron text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 relative overflow-hidden",
  {
    variants: {
      variant: {
        default:
          "bg-jarvis-cyan/10 text-primary border border-jarvis-cyan/30 hover:bg-jarvis-cyan/20 hover:border-jarvis-cyan/60 hover:shadow-glow",
        primary:
          "bg-jarvis-cyan/20 text-primary border-2 border-jarvis-cyan/50 hover:bg-jarvis-cyan/30 hover:shadow-glow-lg",
        ghost:
          "text-primary hover:bg-jarvis-cyan/10 hover:text-primary",
        outline:
          "border border-jarvis-cyan/40 bg-transparent text-primary hover:bg-jarvis-cyan/10",
        danger:
          "bg-destructive/10 text-destructive border border-destructive/30 hover:bg-destructive/20",
        orange:
          "bg-jarvis-orange/10 text-accent border border-jarvis-orange/30 hover:bg-jarvis-orange/20 hover:shadow-glow-orange",
      },
      size: {
        default: "h-10 px-6 py-2",
        sm: "h-8 px-4 text-xs",
        lg: "h-12 px-8 text-base",
        xl: "h-14 px-10 text-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface JarvisButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof jarvisButtonVariants> {
  asChild?: boolean;
}

const JarvisButton = React.forwardRef<HTMLButtonElement, JarvisButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(jarvisButtonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      >
        {children}
        <span className="absolute inset-0 bg-gradient-to-r from-transparent via-jarvis-cyan/10 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700" />
      </Comp>
    );
  }
);
JarvisButton.displayName = "JarvisButton";

export { JarvisButton, jarvisButtonVariants };
