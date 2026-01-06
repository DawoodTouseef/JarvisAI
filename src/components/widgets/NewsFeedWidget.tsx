import { motion, AnimatePresence } from "framer-motion";
import { Newspaper, ExternalLink, TrendingUp, Clock, X } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { useState, useEffect, useMemo } from "react";
import { JarvisButton } from "@/components/ui/JarvisButton";

interface NewsItem {
  id: string;
  title: string;
  source: string;
  category: string;
  timestamp: Date;
  url?: string;
}

const fallbackNews: NewsItem[] = [
  { id: "1", title: "System initialized. No live feed available.", source: "JARVIS", category: "System", timestamp: new Date() },
];

export const NewsFeedWidget = () => {
  const [news, setNews] = useState<NewsItem[]>(fallbackNews);
  const [activeIndex, setActiveIndex] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const NEWS_PAGE_COUNT = 3;
  const totalnews = Math.ceil(news.length / NEWS_PAGE_COUNT);
  // Fetch real-time news (Hacker News Algolia API - public, CORS enabled)
  useEffect(() => {
    let cancelled = false;
    const fetchNews = async () => {
      try {
        const res = await fetch(
          `https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=60`
        );
        if (!res.ok) throw new Error("Failed to fetch news");
        const data = await res.json();
        const items: NewsItem[] = (data.hits || []).map((hit: any) => ({
          id: String(hit.objectID),
          title: hit.title || hit.story_title || "Untitled",
          source: hit.author ? `HN • ${hit.author}` : "Hacker News",
          category: "Tech",
          timestamp: hit.created_at ? new Date(hit.created_at) : new Date(),
          url: hit.url || hit.story_url,
        }));
        if (!cancelled && items.length > 0) {
          setNews(items);
          setActiveIndex(0);
        }
      } catch (e) {
        // Keep fallback
      }
    };
    fetchNews();

    // Refresh every 10 minutes
    const interval = setInterval(fetchNews, 10 * 60 * 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Auto-rotate one item per page unless expanded
  useEffect(() => {
    if (news.length <= 1 || isExpanded) return;
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % news.length);
    }, 8000);
    return () => clearInterval(interval);
  }, [news.length, isExpanded]);

  const formatRelativeTime = (date: Date) => {
    const diffMs = Date.now() - date.getTime();
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const current = useMemo(() => news[Math.max(0, Math.min(activeIndex, news.length - 1))], [news, activeIndex]);

  return (
    <div className="p-4">
      <GlassPanel className={`p-4 h-full flex flex-col ${isExpanded ? 'z-40' : ''}`} onClick={() => setIsExpanded(true)} >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <motion.div
              className="w-2 h-2 rounded-full bg-jarvis-blue"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <Newspaper size={14} className="text-primary" />
            <span className="font-orbitron text-xs text-primary tracking-wider">
              NEWS FEED
            </span>
          </div>
          
          <TrendingUp size={14} className="text-green-400" />
        </div>

        {/* Single-page featured news */}
        <AnimatePresence mode="wait">
          <motion.div
            key={current?.id || activeIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/20 mb-3 cursor-pointer"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-orbitron">
                {current?.category || 'News'}
              </span>
            </div>
            <p className="text-sm font-rajdhani text-foreground leading-tight mb-2 line-clamp-3">
              {current?.title}
            </p>
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>{current?.source}</span>
              <span className="flex items-center gap-1">
                <Clock size={10} />
                {current?.timestamp ? formatRelativeTime(current.timestamp) : ''}
              </span>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Pagination dots */}
        <div className="flex items-center justify-center gap-1 mt-auto">
          {news.map((_, index) => (
            <motion.button
              key={index}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${
                index === activeIndex ? 'bg-primary' : 'bg-primary/30'
              }`}
              onClick={() => setActiveIndex(index)}
              aria-label={`Go to news ${index + 1}`}
            />
          ))}
        </div>
      </GlassPanel>

      {/* Expanded overlay within widget space; overlays items below in the column */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50"
          >
            <GlassPanel className="p-4 flex flex-col border border-jarvis-cyan/40 shadow-glow">
                <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Newspaper size={14} className="text-primary" />
                  <span className="font-orbitron text-xs text-primary tracking-wider">
                    NEWS DETAILS
                  </span>
                </div>
                <button
                  className="text-muted-foreground hover:text-primary transition-colors"
                  onClick={() => setIsExpanded(false)}
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>

              {news.slice(pageIndex, pageIndex+NEWS_PAGE_COUNT).map((item) => (
                <>
              <div className="p-3 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/20 mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-orbitron">
                    {item?.category || 'News'}
                  </span>
                </div>
                <p className="text-base font-rajdhani text-foreground leading-snug mb-2">
                  {item?.title}
                </p>
                <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-3">
                  <span>{item?.source}</span>
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {item?.timestamp ? formatRelativeTime(item.timestamp) : ''}
                  </span>
                </div>
                {item?.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 text-xs text-primary hover:underline"
                  >
                    Read original <ExternalLink size={12} />
                  </a>
                )}
              </div>
                </>
              ))}
              {/* Controls */}
              <div className="mt-auto flex items-center justify-between">
                <button
                  className="text-xs font-orbitron text-primary/80 hover:text-primary"
                  onClick={() => setPageIndex((prev) => (prev - NEWS_PAGE_COUNT + news.length) % news.length)}
                  disabled={pageIndex === 0}
                >
                  Prev
                </button>
                <div className="flex items-center justify-center gap-1">
                  {Array.from({ length: totalnews }, (_, index) => (
                    <div
                      key={index}
                      className={`w-1.5 h-1.5 rounded-full ${index === Math.floor(pageIndex / NEWS_PAGE_COUNT) ? 'bg-primary' : 'bg-primary/30'}`}
                    />
                  ))}
                </div>
                <button
                  className="text-xs font-orbitron text-primary/80 hover:text-primary"
                  onClick={() => setPageIndex((prev) => (prev + NEWS_PAGE_COUNT) % news.length)}
                  disabled={pageIndex === totalnews}
                >
                  Next
                </button>
              </div>
            </GlassPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
