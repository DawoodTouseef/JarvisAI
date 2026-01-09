import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, Calendar, Cpu, HardDrive, Wifi, ChevronDown, ChevronUp, Activity, X } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { StatusCommunication } from "@/lib/client_websocket";
import { toast } from "@/components/ui/use-toast";
import { Communication } from "@/lib/client_websocket";

interface SystemStat {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}

interface ClockStatsProps {
  use24hrFormat?: boolean;
}

export const ClockStats: React.FC<ClockStatsProps> = ({ use24hrFormat = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [time, setTime] = useState(new Date());
  const [uptime , setUptime] = useState<number>(null);
  const [timeKey, setTimeKey] = useState(0);
  const [stats, setStats] = useState<SystemStat[]>([
    { label: "CPU", value: 0, icon: <Cpu size={14} />, color: "jarvis-cyan" },
    { label: "Memory", value: 0, icon: <HardDrive size={14} />, color: "jarvis-blue" },
    { label: "Network", value: 0, icon: <Wifi size={14} />, color: "jarvis-orange" },
    { label: "GPU", value: 0, icon: <Activity size={14} />, color: "jarvis-cyan" },
  ]);
  const [status, setStatus] = useState<string>("Critical");

  useEffect(() => {
    const tick = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(tick);
  }, []);

  // Update time when use24hrFormat changes to force re-render
  useEffect(() => {
    setTimeKey(prev => prev + 1);
  }, [use24hrFormat]);
  useEffect(() => {
    const off = StatusCommunication.onMessage((data) => {
      try {
        const parsed = JSON.parse(data);
        setUptime(parsed["UP_TIME"]);
        if (parsed["Memory"] <= 94.0 || parsed["CPU"] <= 90.0) {
          setStatus("Optimal");
        }
        setStats((prev) =>
          prev.map((stat) => ({
            ...stat,
            value: parsed[stat.label],
          }))
        );
      } catch (_) {}
    });
    return () => { off(); };
  },[]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour12: !use24hrFormat,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  };

  function toDateTime(secs:number) {
    const t = new Date(1970, 0, 1);
    t.setSeconds(secs);
    return t;
  }
  
  return (
    <div className="relative">
      <motion.div
        layout
        className="relative"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <GlassPanel
          className="cursor-pointer hover:border-jarvis-cyan/40 transition-colors p-4 min-w-[200px]"
          onClick={() => setIsExpanded(true)}
        >
          {/* Time display */}
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-primary">
                <Clock size={16} />
                <span className="font-orbitron text-2xl tracking-wider glow-text" key={`time-${timeKey}-${use24hrFormat}`}>
                  {formatTime(time)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground text-xs mt-1">
                <Calendar size={12} />
                <span className="font-rajdhani">{formatDate(time)}</span>
              </div>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              {isExpanded ? <ChevronUp size={20} className="text-primary" /> : <ChevronDown size={20} className="text-primary" />}
            </motion.div>
          </div>
        </GlassPanel>
      </motion.div>

      {/* Expanded overlay above below-widgets */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50"
          >
            <GlassPanel className="p-4 min-w-[200px] border border-jarvis-cyan/40 shadow-glow">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-primary">
                  <Clock size={16} />
                  <span className="font-orbitron text-2xl tracking-wider glow-text" key={`expanded-${timeKey}-${use24hrFormat}`}>
                    {formatTime(time)}
                  </span>
                </div>
                <button
                  className="text-muted-foreground hover:text-primary transition-colors"
                  onClick={(e) => { e.stopPropagation(); setIsExpanded(false); }}
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground text-xs mt-1">
                <Calendar size={12} />
                <span className="font-rajdhani">{formatDate(time)}</span>
              </div>

              <div className="mt-4 pt-4 border-t border-jarvis-cyan/20 space-y-3">
                {stats.map((stat) => (
                  <div key={stat.label} className="flex items-center gap-3">
                    <div className="text-primary">{stat.icon}</div>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-rajdhani text-muted-foreground">
                          {stat.label}
                        </span>
                        {stat.value > 100 ? (
                          <span className="text-xs font-orbitron text-primary">
                            {Math.round(stat.value / 1000000000)} GB
                          </span>
                        ) : (
                          <span className="text-xs font-orbitron text-primary">
                            {Math.round(stat.value)}%
                          </span>
                        )}
                      </div>
                      <div className="h-1.5 bg-jarvis-dark rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{
                            background: `linear-gradient(90deg, hsl(var(--${stat.color})) 0%, hsl(var(--${stat.color}) / 0.5) 100%)`,
                            boxShadow: `0 0 10px hsl(var(--${stat.color}) / 0.5)`,
                          }}
                          initial={{ width: 0 }}
                          animate={{ width: `${stat.value}%` }}
                          transition={{ duration: 0.5, ease: "easeOut" }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-3 border-t border-jarvis-cyan/10 grid grid-cols-2 gap-2 text-xs">
                <div className="text-muted-foreground font-rajdhani">
                  <span className="block text-primary/80">Uptime</span>
                  {uptime ? `${toDateTime(uptime).getDay()}d ${toDateTime(uptime).getHours()}h ${toDateTime(uptime).getMinutes()}m` : "Loading..."}
                </div>
                <div className="text-muted-foreground font-rajdhani text-right">
                  <span className="block text-primary/80">Status</span>
                  <span className={`text-${status === "Critical" ? "cyan" : "green"}-400`}>{status}</span>
                </div>
              </div>
            </GlassPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
