import * as React from "react";
import { cn } from "@/lib/utils";

export interface JarvisInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
}

const JarvisInput = React.forwardRef<HTMLInputElement, JarvisInputProps>(
  ({ className, type, icon, ...props }, ref) => {
    return (
      <div className="relative group">
        {icon && (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-primary/60 group-focus-within:text-primary transition-colors">
            {icon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            "flex h-12 w-full rounded-lg bg-jarvis-dark/60 px-4 py-3 font-rajdhani text-base text-foreground placeholder:text-muted-foreground",
            "border border-jarvis-cyan/20 backdrop-blur-sm",
            "transition-all duration-300",
            "focus:outline-none focus:border-jarvis-cyan/60 focus:shadow-glow-sm focus:bg-jarvis-dark/80",
            "hover:border-jarvis-cyan/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            icon && "pl-12",
            className
          )}
          ref={ref}
          {...props}
        />
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-jarvis-cyan/5 via-transparent to-jarvis-cyan/5 opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none" />
      </div>
    );
  }
);
JarvisInput.displayName = "JarvisInput";

export { JarvisInput };
