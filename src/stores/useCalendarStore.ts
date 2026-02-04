import { create } from 'zustand';

export interface CalendarEvent {
    id: string;
    title: string;
    start: Date;
    end: Date;
    allDay?: boolean;
    resource?: any;
}

interface CalendarState {
    events: CalendarEvent[];
    setEvents: (events: CalendarEvent[]) => void;
    addEvent: (event: CalendarEvent) => void;
    removeEvent: (id: string) => void;
}

export const useCalendarStore = create<CalendarState>((set) => ({
    events: [],
    setEvents: (events) => set({ events }),
    addEvent: (event) => set((state) => ({ events: [...state.events, event] })),
    removeEvent: (id) => set((state) => ({
        events: state.events.filter((e) => e.id !== id),
    })),
}));
