import { GlassPanel } from "@/components/ui/GlassPanel";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { toast } from "sonner";
import { motion } from "framer-motion";

export const QuickAction = () => {
  return (
    <GlassPanel className="cursor-pointer hover:border-jarvis-cyan/40 transition-colors p-4 min-w-[200px]">
      <motion.div animate={{ rotate: 0 }} transition={{ duration: 0.3 }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-jarvis-orange animate-pulse" />
                <span className="font-orbitron text-xs text-accent tracking-wider">
                  QUICK ACTIONS
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {["Analyze", "Scan", "Report", "Archive"].map((action, i) => (
                  <JarvisButton
                    key={action}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => toast.info(`${action} initiated`)}
                  >
                    {action}
                  </JarvisButton>
                ))}
              </div>
      </motion.div>
    </GlassPanel>
  )
}