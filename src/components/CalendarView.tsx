import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import {format} from 'date-fns/format'
import {parse} from 'date-fns/parse'
import {startOfWeek} from 'date-fns/startOfWeek'
import {getDay} from 'date-fns/getDay'
import {enUS} from 'date-fns/locale/en-US'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import { GlassPanel } from '@/components/ui/GlassPanel'
import { useCalendarStore } from '@/stores/useCalendarStore'
import { useState } from 'react'

const locales = {
    'en-US': enUS,
}

const localizer = dateFnsLocalizer({
    format,
    parse,
    startOfWeek,
    getDay,
    locales,
})

export const CalendarView = () => {
    const { events } = useCalendarStore();
    const [view, setView] = useState('month');
    // Custom styling for calendar events to match Jarvis theme
    const eventStyleGetter = (event, start, end, isSelected) => {
        return {
            style: {
                backgroundColor: 'hsl(185 100% 50% / 0.2)',
                borderColor: 'hsl(185 100% 50%)',
                color: 'hsl(185 100% 50%)',
                borderRadius: '4px',
                border: '1px solid'
            }
        };
    };

    return (
        <GlassPanel className="h-full flex flex-col p-0 overflow-hidden">
            <div className="p-4 border-b border-jarvis-cyan/20">
                <h2 className="text-xl font-orbitron text-jarvis-cyan">Temporal Schedule</h2>
            </div>
            <div className="flex-1 p-4 main-calendar-container">
                <style>{`
                    .rbc-calendar { color: #a1a1aa; font-family: 'Rajdhani', sans-serif; }
                    .rbc-toolbar button { color: #06b6d4; border-color: #06b6d4; }
                    .rbc-toolbar button:hover { bg-color: #06b6d4; color: black; }
                    .rbc-toolbar button.rbc-active { background-color: #06b6d4; color: black; }
                    .rbc-off-range-bg { background: transparent; }
                    .rbc-today { background-color: rgba(6, 182, 212, 0.1); }
                `}</style>
                <Calendar
                    localizer={localizer}
                    events={events}
                    startAccessor="start"
                    endAccessor="end"
                    style={{ height: '100%' }}
                    eventPropGetter={eventStyleGetter}
                />
            </div>
        </GlassPanel>
    )
}
