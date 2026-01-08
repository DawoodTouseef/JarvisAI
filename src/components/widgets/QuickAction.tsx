import { GlassPanel } from "@/components/ui/GlassPanel";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { ChevronRight, ChevronLeft } from "lucide-react";
import { useState } from "react";

export const QuickAction = () => {
  const [currentView, setCurrentView] = useState<'main'>('main');
  
  

  
  const renderMainView = () => (
    <>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 rounded-full bg-jarvis-orange animate-pulse" />
        <span className="font-orbitron text-xs text-accent tracking-wider">
          QUICK ACTIONS
        </span>
      </div>
      
      <div className="space-y-3">
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground">No quick actions available</p>
        </div>
      </div>
    </>
  );
  

  

  

  


  return (
    <GlassPanel className="cursor-pointer hover:border-jarvis-cyan/40 transition-colors p-4 min-w-[320px] max-w-[400px]">
      <motion.div animate={{ rotate: 0 }} transition={{ duration: 0.3 }}>
        {currentView === 'main' && renderMainView()}
      </motion.div>
    </GlassPanel>
  )
}