import { motion } from "framer-motion";

export const ScanLines = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
      {/* Horizontal scan line */}
      <motion.div
        className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-jarvis-cyan/40 to-transparent"
        initial={{ top: "-2px" }}
        animate={{ top: "100%" }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "linear",
          repeatDelay: 1,
        }}
      />

      {/* Static scan lines overlay */}
      <div className="absolute inset-0 scan-lines opacity-30" />

      {/* Vignette effect */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 0%, hsl(220 30% 3% / 0.4) 100%)",
        }}
      />
    </div>
  );
};
