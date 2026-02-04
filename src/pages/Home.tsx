import { AudioSpectrum } from "@/components/AudioSpectrum";
import { motion } from "framer-motion";

export const Home = () => {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center h-full w-full"
        >
            <AudioSpectrum />
        </motion.div>
    );
};
