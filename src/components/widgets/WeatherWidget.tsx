import { motion } from "framer-motion";
import { Cloud, Sun, CloudRain, Wind, Droplets, Thermometer } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { useState, useEffect } from "react";

interface WeatherData {
  temperature: number;
  condition: "sunny" | "cloudy" | "rainy";
  humidity: number;
  windSpeed: number; // km/h
  location: string;
  feelsLike: number;
}

interface WeatherWidgetProps {
  // Human-readable location name (e.g., "New York", "Paris", "Tokyo").
  // Defaults to "New York" for backward compatibility.
  location?: string;
}

// Map Open-Meteo weather codes to simplified conditions used by the UI
const mapWeatherCodeToCondition = (code: number | undefined): WeatherData["condition"] => {
  if (code === undefined || code === null) return "cloudy";
  if (code === 0 || code === 1) return "sunny"; // Clear or mainly clear
  if ([2, 3, 45, 48].includes(code)) return "cloudy"; // Partly cloudy / fog
  const rainyCodes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99];
  if (rainyCodes.includes(code)) return "rainy"; // Drizzle/Rain/Thunderstorms
  // Snow and other codes fallback to cloudy for this UI
  return "cloudy";
};

export const WeatherWidget = ({ location = "Bangalore" }: WeatherWidgetProps) => {
  const [weather, setWeather] = useState<WeatherData>({
    temperature: 0,
    condition: "sunny",
    humidity: 0,
    windSpeed: 0,
    location,
    feelsLike: 0,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real-time weather when location changes and periodically refresh
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    const fetchWeather = async () => {
      try {
        setLoading(true);
        setError(null);

        // 1) Geocode the location to coordinates
        const geoRes = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(location)}&count=1&language=en&format=json`,
          { signal: controller.signal }
        );
        if (!geoRes.ok) throw new Error("Geocoding failed");
        const geo = await geoRes.json();
        if (!geo.results || geo.results.length === 0) throw new Error("Location not found");

        const place = geo.results[0];
        const { latitude, longitude, name, country_code, admin1 } = place;
        const displayLocation = [name, admin1, country_code].filter(Boolean).join(", ");

        // 2) Fetch current weather
        const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code&wind_speed_unit=kmh&timezone=auto`;
        const wRes = await fetch(weatherUrl, { signal: controller.signal });
        if (!wRes.ok) throw new Error("Weather fetch failed");
        const w = await wRes.json();

        // Prefer new `current` block; fallback to older `current_weather` if needed
        const current = w.current ?? null;
        const fallback = w.current_weather ?? null;

        const temp = (current?.temperature_2m ?? fallback?.temperature) ?? 0;
        const humidity = (current?.relative_humidity_2m ?? 0) as number;
        const wind = (current?.wind_speed_10m ?? fallback?.windspeed ?? 0) as number;
        const feels = (current?.apparent_temperature ?? temp) as number;
        const code = (current?.weather_code ?? fallback?.weathercode) as number | undefined;

        if (cancelled) return;
        setWeather({
          temperature: temp,
          humidity,
          windSpeed: wind,
          feelsLike: feels,
          condition: mapWeatherCodeToCondition(code),
          location: displayLocation || location,
        });
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || "Failed to fetch weather");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchWeather();
    // Periodic refresh every 10 minutes
    const interval = setInterval(fetchWeather, 10 * 60 * 1000);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
    };
  }, [location]);

  const WeatherIcon = weather.condition === "sunny" ? Sun : weather.condition === "rainy" ? CloudRain : Cloud;

  return (
    <GlassPanel className="p-4 h-full">
      <div className="flex items-center gap-2 mb-3">
        <motion.div
          className="w-2 h-2 rounded-full bg-yellow-400"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span className="font-orbitron text-xs text-primary tracking-wider">
          WEATHER
        </span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs text-muted-foreground font-rajdhani mb-1">
            {error ? `Error: ${error}` : weather.location}
          </p>
          <motion.p
            key={Math.round(weather.temperature)}
            initial={{ scale: 1.1, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-3xl font-orbitron text-foreground"
          >
            {loading ? "--" : Math.round(weather.temperature)}°
          </motion.p>
        </div>
        <motion.div
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ duration: 4, repeat: Infinity }}
          className="text-yellow-400"
        >
          <WeatherIcon size={40} />
        </motion.div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <motion.div
          className="flex flex-col items-center p-2 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/10"
          whileHover={{ scale: 1.05, borderColor: "hsl(185 100% 50% / 0.3)" }}
        >
          <Droplets size={14} className="text-blue-400 mb-1" />
          <span className="text-xs font-orbitron text-foreground">{loading ? "--" : Math.round(weather.humidity)}%</span>
          <span className="text-[10px] text-muted-foreground font-rajdhani">Humidity</span>
        </motion.div>
        <motion.div
          className="flex flex-col items-center p-2 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/10"
          whileHover={{ scale: 1.05, borderColor: "hsl(185 100% 50% / 0.3)" }}
        >
          <Wind size={14} className="text-gray-400 mb-1" />
          <span className="text-xs font-orbitron text-foreground">{loading ? "--" : Math.round(weather.windSpeed)}</span>
          <span className="text-[10px] text-muted-foreground font-rajdhani">km/h</span>
        </motion.div>
        <motion.div
          className="flex flex-col items-center p-2 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/10"
          whileHover={{ scale: 1.05, borderColor: "hsl(185 100% 50% / 0.3)" }}
        >
          <Thermometer size={14} className="text-red-400 mb-1" />
          <span className="text-xs font-orbitron text-foreground">{loading ? "--" : Math.round(weather.feelsLike)}°</span>
          <span className="text-[10px] text-muted-foreground font-rajdhani">Feels</span>
        </motion.div>
      </div>
    </GlassPanel>
  );
};
