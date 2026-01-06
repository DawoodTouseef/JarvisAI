import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { LogOut, Settings, Bell, Shield,Wifi,Volume2, BatteryFull, Home} from "lucide-react";
import { AudioSpectrum } from "@/components/AudioSpectrum";
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

const Dashboard = () => {
  const navigate = useNavigate();
  const [time, setTime] = useState(new Date());
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isSystemTrayOpen, setIsSystemTrayOpen] = useState(false);
  const [startbutton,setstartbutton] = useState(false)

  const transcription = useTranscriptionStore((state) => state.text);
  const [isclockOpen, setIsClockOpen] = useState(false);
  const handleMouseMove = useCallback((e: MouseEvent) => {
    const x = (e.clientX / window.innerWidth - 0.5) * 20;
    const y = (e.clientY / window.innerHeight - 0.5) * 20;
    setMousePosition({ x, y });
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);

  const handleLogout = async() => {
    
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
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour12: true,
      hour: "2-digit",
      minute: "2-digit",
    });
  };
  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "numeric",
      day: "numeric",
      year: "numeric",
      formatMatcher:"basic"
    });
  };
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
            <JarvisButton variant="ghost" size="icon"><Settings size={18} /></JarvisButton>
            <JarvisButton variant="ghost" size="icon" onClick={handleLogout}><LogOut size={18} /></JarvisButton>
          </div>
        </motion.header>

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-180px)]">
          {/* Left Column */}
          <div className="lg:col-span-3 space-y-4">
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} className="h-48 lg:h-56">
              <GlassPanel className="h-full p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-jarvis-cyan animate-pulse" />
                  <span className="font-orbitron text-xs text-primary tracking-wider">GLOBAL NETWORK</span>
                </div>
                <div className="h-[calc(100%-30px)]"><Globe3D /></div>
              </GlassPanel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="h-50">
              <WeatherWidget />
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="h-50">
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
          className="cursor-pointer hover:border-jarvis-cyan/40 transition-colors p-4 min-w-[200px]">
                   <div className="border border-green">
                    <JarvisInput placeholder="Search for apps  and documents"
                    style={{
                      borderColor:"AppWorkspace",
                      borderRadius:"2%"  
                    }}
                    
                    ></JarvisInput>
                   </div>
                </GlassPanel>
                </motion.div>
                </div>
              )}
            </motion.div>
          </div>

          {/* Center */}
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="lg:col-span-6 flex flex-col items-center justify-center">
            <AudioSpectrum />
          </motion.div>
          {/* Right - Clock & Stats */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="lg:col-span-3 space-y-4"
            style={{
              transform: `translate(${mousePosition.x * 0.3}px, ${mousePosition.y * 0.3}px)`,
            }}
          >
            <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="lg:col-span-3 space-y-4"
            style={{
              transform: `translate(${mousePosition.x * 0.3}px, ${mousePosition.y * 0.3}px)`,
            }}
          >
            <ClockStats/>
          </motion.div>
          
            {/* Quick actions panel */}
            <NewsFeedWidget />

            {isSystemTrayOpen && (
              <GlassPanel className="p-4 ">
                <QuickAction />
              </GlassPanel>
            )}
            {isclockOpen && (
              <GlassPanel className="absolute bottom-[50px] right-5  p-4">
                <CalendarWidget />
              </GlassPanel>
            )}
          </motion.div>
        </div>
      </motion.div>

      {/* Corner decorations */}
      <div className="absolute top-4 left-4 w-12 h-12 border-l border-t border-jarvis-cyan/20" />
      <div className="absolute top-4 right-4 w-12 h-12 border-r border-t border-jarvis-cyan/20" />
      <div className="absolute bottom-4 left-4 w-12 h-12 border-l border-b border-jarvis-cyan/20" />
      <div className="absolute bottom-4 right-4 w-12 h-12 border-r border-b border-jarvis-cyan/20" />

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
        className="absolute bottom-0 left-0 right-0 z-50 pointer-events-auto h-10 glass-panel rounded-none border-x-0 border-b-0 flex items-center justify-between px-6">
          <JarvisButton size="icon" variant="ghost" 
              className="left-0 justify-left"
              onClick={()=>{
                setstartbutton(!startbutton)
              }}
              >
                <Home size={14}/>

              </JarvisButton>
           
        <div className="text-xs text-muted-foreground font-orbitron tracking-wider flex items-center gap-2 relative">
            <JarvisButton
              variant="ghost"
              size="sm"
              className={`pointer-events-auto px-3 min-w-[110px] transition-colors ${isSystemTrayOpen ? 'border border-jarvis-cyan/40' : 'border border-transparent'}`}
              onClick={() => {
                setIsSystemTrayOpen((v) => !v);
              }}
            >
              <div className="flex items-center justify-between w-full pointer-events-none">
                <Wifi size={16} />
                <Volume2 size={16} />
                <BatteryFull size={16} />
              </div>
            </JarvisButton>
            <div className="flex flex-col leading-tight">
              <JarvisButton variant="ghost"  className="pointer-events-auto px-3 min-w-[80px]"
                onClick={()=>setIsClockOpen(!isclockOpen)}
              >
                <span className="font-orbitron">{formatTime(time)}</span>
              </JarvisButton>
            </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
