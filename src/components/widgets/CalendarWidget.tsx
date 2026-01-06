import { motion } from "framer-motion";
import { Calendar, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { useState } from "react";

interface Event {
  id: string;
  title: string;
  time: string;
  type: "meeting" | "reminder" | "task";
}

const mockEvents: Event[] = [
  { id: "1", title: "System Diagnostic", time: "09:00", type: "task" },
  { id: "2", title: "Security Review", time: "11:30", type: "meeting" },
  { id: "3", title: "Database Backup", time: "14:00", type: "reminder" },
  { id: "4", title: "Performance Analysis", time: "16:30", type: "task" },
];

const typeColors = {
  meeting: "bg-jarvis-cyan text-jarvis-cyan",
  reminder: "bg-jarvis-orange text-jarvis-orange",
  task: "bg-jarvis-blue text-jarvis-blue",
};

export const CalendarWidget = () => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [events] = useState<Event[]>(mockEvents);

  const daysOfWeek = ["S", "M", "T", "W", "T", "F", "S"];
  const today = new Date();

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    return { firstDay, daysInMonth };
  };

  const { firstDay, daysInMonth } = getDaysInMonth(selectedDate);

  const navigateMonth = (direction: number) => {
    setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() + direction, 1));
  };
  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      day: "2-digit",
      month: "long",
    });
  };
  return (
    <GlassPanel className="p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <motion.div
            className="w-2 h-2 rounded-full bg-jarvis-orange"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <Calendar size={14} className="text-accent" />
          <span className="font-orbitron text-xs text-accent tracking-wider">
            {formatDate(new Date())}
          </span>
        </div>
      </div>

      {/* Month navigation */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => navigateMonth(-1)}
          className="p-1 hover:bg-jarvis-cyan/10 rounded transition-colors"
        >
          <ChevronLeft size={14} className="text-muted-foreground" />
        </button>
        <span className="font-orbitron text-xs text-foreground">
          {selectedDate.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </span>
        <button
          onClick={() => navigateMonth(1)}
          className="p-1 hover:bg-jarvis-cyan/10 rounded transition-colors"
        >
          <ChevronRight size={14} className="text-muted-foreground" />
        </button>
      </div>

      {/* Mini calendar */}
      <div className="grid grid-cols-7 gap-1 mb-4">
        {daysOfWeek.map((day) => (
          <div key={day} className="text-center text-[10px] text-muted-foreground font-rajdhani">
            {day}
          </div>
        ))}
        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const isToday =
            day === today.getDate() &&
            selectedDate.getMonth() === today.getMonth() &&
            selectedDate.getFullYear() === today.getFullYear();
          return (
            <motion.div
              key={day}
              whileHover={{ scale: 1.2 }}
              className={`text-center text-[10px] font-rajdhani p-1 rounded cursor-pointer transition-colors ${
                isToday
                  ? "bg-primary text-primary-foreground font-bold"
                  : "text-foreground/70 hover:bg-jarvis-cyan/10"
              }`}
            >
              {day}
            </motion.div>
          );
        })}
      </div>

      {/* Today's events */}
      <div className="flex-1 space-y-2">
        <p className="text-[10px] text-muted-foreground font-rajdhani uppercase tracking-wider mb-2">
          Today's Events
        </p>
        {events.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02, x: 5 }}
            className="flex items-center gap-2 p-2 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/10 cursor-pointer"
          >
            <div className={`w-1 h-8 rounded-full ${typeColors[event.type].split(" ")[0]}`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-rajdhani text-foreground truncate">{event.title}</p>
              <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Clock size={8} />
                {event.time}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </GlassPanel>
  );
};
