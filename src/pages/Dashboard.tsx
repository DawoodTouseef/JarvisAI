import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate, Outlet } from "react-router-dom";
import { LogOut, Settings, Bell, Shield, Wifi, Volume2, BatteryFull, Home, Calendar, CheckSquare, FileText } from "lucide-react";
import { Globe3D } from "@/components/Globe3D";
import { ClockStats } from "@/components/ClockStats";
import { ParticleField } from "@/components/ParticleField";
import { ScanLines } from "@/components/ScanLines";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { WeatherWidget } from "@/components/widgets/WeatherWidget";
import { NewsFeedWidget } from "@/components/widgets/NewsFeedWidget";
import { CalendarWidget } from "@/components/widgets/CalendarWidget"
import { toast } from "sonner";
import { useTranscriptionStore } from "@/stores/transcription";
import { QuickAction } from "@/components/widgets/QuickAction";
import { JarvisInput } from "@/components/ui/JarvisInput";
import Video from "@/components/Video";
import { SettingsWindow } from "@/components/SettingsWindow";
import { NotesWindow } from "@/components/NotesWindow";
import { CalendarWindow } from "@/components/CalendarWindow";
import { Communication, AgentCommunication } from "@/lib/client_websocket";


const Dashboard = () => {
  const navigate = useNavigate();
  const [time, setTime] = useState(new Date());
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isSystemTrayOpen, setIsSystemTrayOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [useVideo, setUseVideo] = useState(false); // Default to true
  const [startbutton, setstartbutton] = useState(false)
  const [city, setCity] = useState('New York'); // Default city
  const [notes, setNotes] = useState(false);
  const [calendar, setCalendar] = useState(false);
  const [tasks, setTasks] = useState(false);
  const [use24hrFormat, setUse24hrFormat] = useState(false);

  const transcription = useTranscriptionStore((state) => state.text);
  const [isClockOpen, setIsClockOpen] = useState(false);
  const handleMouseMove = useCallback((e: MouseEvent) => {
    const x = (e.clientX / window.innerWidth - 0.5) * 20;
    const y = (e.clientY / window.innerHeight - 0.5) * 20;
    setMousePosition({ x, y });
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);
  useEffect(() => {
    const tick = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(tick);
  }, []);

  const loadSettings = async () => {
    try {
      // Send a message to the server to get settings
      Communication.sendMessage(JSON.stringify({
        type: 'get_settings',
        request_id: 'load_settings'
      }));

      // Set up a temporary listener for the response
      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'load_settings' && data.type === 'settings_response') {
            setUseVideo(data.payload.useVideo || false);
            setCity(data.payload.city || 'New York'); // Update city from settings
            setUse24hrFormat(data.payload.use24hrFormat || false); // Update 24-hour format from settings
            off(); // Remove the listener after receiving the response
          }
        } catch (e) {
          console.error('Error parsing settings response:', e);
        }
      });
    } catch (error) {
      console.error('Error loading settings:', error);
      toast.error('Failed to load settings');
    } finally {
    }
  };

  // Listen for settings updates
  const handleSettingsUpdate = (msg: string) => {
    try {
      const data = JSON.parse(msg);
      if (data.type === 'settings_response' && data.request_id !== 'load_settings') {
        // This is an update from the settings panel
        if (data.payload && data.payload.city !== undefined) {
          setCity(data.payload.city);
        }
        if (data.payload && data.payload.useVideo !== undefined) {
          setUseVideo(data.payload.useVideo);
        }
        if (data.payload && data.payload.use24hrFormat !== undefined) {
          setUse24hrFormat(data.payload.use24hrFormat);
        }
      }
    } catch (e) {
      console.error('Error parsing settings update:', e);
    }
  };

  useEffect(() => {
    const settingsUpdateListener = Communication.onMessage(handleSettingsUpdate);

    // Agent Event Listener
    const agentListener = AgentCommunication.onMessage((msg) => {
      try {
        const data = JSON.parse(msg);
        // Handle other notifications
        if (data.type === 'agent_response' && data.status === 'completed') {
          toast.success("Task Completed", { description: data.result.message || "Action finished." });
        }
      } catch (e) {
        console.error("Agent message error", e);
      }
    });

    return () => {
      settingsUpdateListener();
      agentListener();
    };
  }, []);

  const handleLogout = async () => {

    const res = await fetch('/api/auths/signout', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        "Authorization": `Bearer ${localStorage.getItem("jarvis:token") || ''}`
      },
    });
    if (res.ok || res.status === 200) {
      localStorage.removeItem("jarvis:token");
      toast.info("Session terminated", {
        description: "JARVIS systems shutting down...",
      });
      navigate("/login");
    }
  };
  const formatTime = (date: Date, use24HourFormat: boolean) => {
    return date.toLocaleTimeString("en-US", {
      hour12: !use24HourFormat,
      hour: "2-digit",
      minute: "2-digit",
    });
  };
  useEffect(() => {
    loadSettings();
  }, []);

  // Force time update when format changes
  useEffect(() => {
    setTime(new Date());
  }, [use24hrFormat]);
  return (
    <div className="min-h-screen relative overflow-hidden">
      <ParticleField />
      <ScanLines />

      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: `linear-gradient(hsl(185 100% 50% / 0.05) 1px, transparent 1px), linear-gradient(90deg, hsl(185 100% 50% / 0.05) 1px, transparent 1px)`,
        backgroundSize: "80px 80px",
      }} />

      <motion.div className="relative z-10 min-h-screen p-4 md:p-6" style={{
        transform: `translate(${mousePosition.x * 0.5}px, ${mousePosition.y * 0.5}px)`,
      }}>
        {/* Header */}
        <motion.header initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <motion.div className="w-10 h-10 rounded-full border-2 border-jarvis-cyan/50 flex items-center justify-center"
              animate={{ boxShadow: ["0 0 10px hsl(185 100% 50% / 0.3)", "0 0 20px hsl(185 100% 50% / 0.5)", "0 0 10px hsl(185 100% 50% / 0.3)"] }}
              transition={{ duration: 2, repeat: Infinity }}>
              <Shield size={20} className="text-primary" />
            </motion.div>
            <div>
              <h1 className="font-orbitron text-xl md:text-2xl text-foreground glow-text tracking-wider">J.A.R.V.I.S</h1>
              <p className="text-xs text-muted-foreground font-rajdhani tracking-widest uppercase">Just A Rather Very Intelligent System</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <JarvisButton variant="ghost" size="icon"><Bell size={18} /></JarvisButton>
            <JarvisButton variant="ghost" size="icon" onClick={() => setIsSettingsOpen(true)}><Settings size={18} /></JarvisButton>
            <JarvisButton variant="ghost" size="icon" onClick={handleLogout}><LogOut size={18} /></JarvisButton>
          </div>
        </motion.header>

        {/* Main Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3 md:gap-4 min-h-[calc(100vh-140px)] md:min-h-[calc(100vh-160px)]">
          {/* Left Column */}
          <div className="md:col-span-1 lg:col-span-3 flex flex-col gap-3 md:gap-4">
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} className="flex-shrink-0 h-48 md:h-56 lg:h-64">
              <GlassPanel className="h-full p-3 md:p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-jarvis-cyan animate-pulse" />
                  <span className="font-orbitron text-xs text-primary tracking-wider">GLOBAL NETWORK</span>
                </div>
                <div className="h-[calc(100%-30px)]"><Globe3D /></div>
              </GlassPanel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="flex-shrink-0">
              <WeatherWidget location={city} />
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="flex-1">
              {startbutton && (
                <div className="relative">
                  <motion.div
                    layout
                    className="relative"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                  >
                    <GlassPanel
                      className="cursor-pointer hover:border-jarvis-cyan/40 transition-colors p-3 md:p-4 w-full">
                      <div className="border border-green">
                        <JarvisInput placeholder="Search for apps and documents"
                          style={{
                            borderColor: "AppWorkspace",
                            borderRadius: "2%"
                          }}
                        ></JarvisInput>
                      </div>

                      <div className="grid grid-cols-3 gap-2 mt-4">
                        <JarvisButton variant="ghost" className="flex flex-col gap-1 h-auto py-2 text-xs md:text-sm" onClick={() => { setTasks(true); setstartbutton(false); }}>
                          <CheckSquare size={18} className="text-jarvis-cyan" />
                          <span className="text-[10px]">Tasks</span>
                        </JarvisButton>
                        <JarvisButton variant="ghost" className="flex flex-col gap-1 h-auto py-2 text-xs md:text-sm" onClick={() => { setCalendar(true); setstartbutton(false); }}>
                          <Calendar size={18} className="text-jarvis-cyan" />
                          <span className="text-[10px]">Calendar</span>
                        </JarvisButton>
                        <JarvisButton variant="ghost" className="flex flex-col gap-1 h-auto py-2 text-xs md:text-sm" onClick={() => { setNotes(true); setstartbutton(false); }}>
                          <FileText size={18} className="text-jarvis-cyan" />
                          <span className="text-[10px]">Notes</span>
                        </JarvisButton>
                      </div>
                    </GlassPanel>
                  </motion.div>
                </div>
              )}
            </motion.div>
          </div>

          {/* Center - Main Content */}
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="md:col-span-1 lg:col-span-6 flex flex-col items-center justify-center p-3 md:p-4 min-h-96">
            <Outlet />
          </motion.div>

          {/* Right - Clock & Stats */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="md:col-span-2 lg:col-span-3 flex flex-col gap-3 md:gap-4"
            style={{
              transform: `translate(${mousePosition.x * 0.3}px, ${mousePosition.y * 0.3}px)`,
            }}
          >
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="flex-shrink-0"
            >
              <ClockStats use24hrFormat={use24hrFormat} />
            </motion.div>

            {/* Quick actions panel */}
            <div className="flex-1 overflow-y-auto">
              <NewsFeedWidget />
            </div>

            {useVideo && (
              <div className="flex-shrink-0">
                <Video />
              </div>
            )}
          </motion.div>
        </div>

        {/* System Tray and Clock Popups */}
        {isSystemTrayOpen && (
          <div className="fixed bottom-20 right-6 z-40 md:bottom-24 md:right-8">
            <GlassPanel className="p-3 md:p-4">
              <QuickAction />
            </GlassPanel>
          </div>
        )}
        {isClockOpen && (
          <div className="fixed bottom-20 right-6 z-40 md:bottom-24 md:right-8">
            <GlassPanel className="p-3 md:p-4 max-w-sm">
              <CalendarWidget />
            </GlassPanel>
          </div>
        )}
      </motion.div>

      {/* Corner decorations */}
      <div className="absolute top-4 left-4 w-8 md:w-12 h-8 md:h-12 border-l border-t border-jarvis-cyan/20" />
      <div className="absolute top-4 right-4 w-8 md:w-12 h-8 md:h-12 border-r border-t border-jarvis-cyan/20" />
      <div className="absolute bottom-10 left-4 w-8 md:w-12 h-8 md:h-12 border-l border-b border-jarvis-cyan/20" />
      <div className="absolute bottom-10 right-4 w-8 md:w-12 h-8 md:h-12 border-r border-b border-jarvis-cyan/20" />

      {/* Taskbar */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.6 }}
        className="fixed bottom-0 left-0 right-0 z-50 pointer-events-auto h-10 glass-panel rounded-none border-x-0 border-b-0 flex items-center justify-between px-3 md:px-6"
      >
        <JarvisButton 
          size="icon" 
          variant="ghost"
          className="flex-shrink-0"
          onClick={() => setstartbutton(!startbutton)}
        >
          <Home size={14} />
        </JarvisButton>

        <div className="text-xs text-muted-foreground font-orbitron tracking-wider flex items-center gap-1 md:gap-2">
          <JarvisButton
            variant="ghost"
            size="sm"
            className={`pointer-events-auto px-2 md:px-3 transition-colors flex-shrink-0 ${isSystemTrayOpen ? 'border border-jarvis-cyan/40' : 'border border-transparent'}`}
            onClick={() => setIsSystemTrayOpen((v) => !v)}
          >
            <div className="flex items-center justify-between w-full pointer-events-none gap-1">
              <Wifi size={12} className="hidden md:inline" />
              <Volume2 size={12} />
              <BatteryFull size={12} className="hidden md:inline" />
            </div>
          </JarvisButton>
          <div className="flex items-center">
            <JarvisButton 
              variant="ghost" 
              className="pointer-events-auto px-2 md:px-3 flex-shrink-0 text-xs"
              onClick={() => setIsClockOpen(!isClockOpen)}
            >
              <span className="font-orbitron">{formatTime(time, use24hrFormat)}</span>
            </JarvisButton>
          </div>
        </div>
      </motion.div>
      
      <SettingsWindow
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentUseVideo={useVideo}
        onUseVideoChange={setUseVideo}
        currentCity={city}
        onCityChange={setCity}
      />

      <NotesWindow
        isOpen={notes}
        onClose={() => setNotes(false)}
      />

      <CalendarWindow
        isOpen={calendar}
        onClose={() => setCalendar(false)}
      />
      
    </div>
  );
};

export default Dashboard;
