import { motion } from "framer-motion";
import { useAgentSystemStore } from "@/stores/agentSystem";

export const AgentActivityFeed = () => {
  const activity = useAgentSystemStore((s) => s.activity);

  if (!activity.length) {
    return (
      <div className="mt-4 text-xs text-muted-foreground font-orbitron tracking-wider">
        ACTIVITY FEED EMPTY
      </div>
    );
  }

  return (
    <div className="mt-4 w-full max-w-md">
      <div className="text-xs text-muted-foreground font-orbitron tracking-wider mb-2">
        AGENT ACTIVITY
      </div>
      <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
        {activity.slice(0, 6).map((item) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs bg-jarvis-dark/40 border border-jarvis-cyan/20 rounded-md px-3 py-2"
          >
            <div className="text-primary font-rajdhani tracking-wide">
              {item.agent ? `${item.agent} → ` : ""}{item.message}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              {new Date(item.timestamp).toLocaleTimeString()}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
