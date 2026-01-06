import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface HexagonFrameProps {
  children: React.ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  animated?: boolean;
}

const sizeClasses = {
  sm: "w-32 h-36",
  md: "w-48 h-52",
  lg: "w-64 h-72",
  xl: "w-80 h-88",
};

export const HexagonFrame = ({
  children,
  className,
  size = "lg",
  animated = true,
}: HexagonFrameProps) => {
  return (
    <div className={cn("relative", sizeClasses[size], className)}>
      {/* Outer glow ring */}
      {animated && (
        <motion.div
          className="absolute inset-0 hexagon bg-jarvis-cyan/5"
          animate={{
            boxShadow: [
              "0 0 20px hsl(185 100% 50% / 0.2)",
              "0 0 40px hsl(185 100% 50% / 0.4)",
              "0 0 20px hsl(185 100% 50% / 0.2)",
            ],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      )}

      {/* Rotating border */}
      <motion.div
        className="absolute inset-2 hexagon border-2 border-jarvis-cyan/30"
        animate={animated ? { rotate: 360 } : {}}
        transition={{
          duration: 60,
          repeat: Infinity,
          ease: "linear",
        }}
      />

      {/* Inner content panel */}
      <div className="absolute inset-4 hexagon glass-panel flex items-center justify-center">
        {children}
      </div>

      {/* Corner accents */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="hexGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(185 100% 50% / 0.6)" />
            <stop offset="50%" stopColor="hsl(210 100% 60% / 0.3)" />
            <stop offset="100%" stopColor="hsl(185 100% 50% / 0.6)" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};
