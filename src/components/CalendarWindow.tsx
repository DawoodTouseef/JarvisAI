import { useState, useEffect } from 'react';
import { GlassPanel } from './ui/GlassPanel';
import { JarvisButton } from './ui/JarvisButton';
import { Plus, Trash2, ArrowLeft, Save } from 'lucide-react';
import { Communication } from '@/lib/client_websocket';
import { useCalendarStore, CalendarEvent } from '@/stores/useCalendarStore';
import { toast } from 'sonner';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { CalendarView } from './CalendarView';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface CalendarWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export enum EventType {
  TASK = 'Task',
  MEETING = 'Meeting',
  REMINDER = 'Reminder',
}

export const CalendarWindow = ({ isOpen, onClose }: CalendarWindowProps) => {
  const { events, setEvents, addEvent, removeEvent } = useCalendarStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: new Date().toISOString().split('T')[0],
    time: '09:00',
    type: EventType.TASK,
  });

  // Load events from server via WebSocket
  const loadEvents = async () => {
    try {
      setIsLoading(true);
      Communication.sendMessage(JSON.stringify({
        type: 'get_events',
        request_id: 'load_calendar_events'
      }));

      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'load_calendar_events' && data.type === 'events_response') {
            // Convert events to CalendarEvent format
            const calendarEvents = (data.payload?.events || []).map((event: any) => ({
              id: event.id,
              title: event.name || event.title,
              start: new Date(event.dateTime || event.start),
              end: new Date(event.dateTime || event.end || event.dateTime),
              allDay: event.allDay || false,
              resource: event,
            }));
            setEvents(calendarEvents);
            off();
          }
        } catch (e) {
          console.error('Error parsing events response:', e);
        }
      });
    } catch (error) {
      console.error('Error loading events:', error);
      toast.error('Failed to load events');
    } finally {
      setIsLoading(false);
    }
  };

  // Create new event
  const createEvent = async () => {
    if (!formData.title) {
      toast.error('Please enter an event title');
      return;
    }

    const newEvent = {
      id: crypto.randomUUID(),
      name: formData.title,
      description: formData.description,
      date: formData.date,
      time: formData.time,
      type: formData.type,
      dateTime: new Date(`${formData.date}T${formData.time}`).toISOString(),
    };

    try {
      Communication.sendMessage(JSON.stringify({
        type: 'save_event',
        request_id: `save_event_${Date.now()}`,
        payload: newEvent
      }));

      // Add to local store
      const calendarEvent: CalendarEvent = {
        id: newEvent.id,
        title: newEvent.name,
        start: new Date(newEvent.dateTime),
        end: new Date(new Date(newEvent.dateTime).getTime() + 60 * 60 * 1000), // 1 hour duration
        resource: newEvent,
      };
      addEvent(calendarEvent);

      // Reset form
      setFormData({
        title: '',
        description: '',
        date: new Date().toISOString().split('T')[0],
        time: '09:00',
        type: EventType.TASK,
      });
      setShowForm(false);
      toast.success('Event created and will appear in calendar');
    } catch (error) {
      console.error('Error creating event:', error);
      toast.error('Failed to create event');
    }
  };

  // Delete event
  const deleteEvent = async (eventId: string) => {
    try {
      Communication.sendMessage(JSON.stringify({
        type: 'delete_event',
        request_id: `delete_event_${Date.now()}`,
        payload: { id: eventId }
      }));

      removeEvent(eventId);
      toast.success('Event deleted');
    } catch (error) {
      console.error('Error deleting event:', error);
      toast.error('Failed to delete event');
    }
  };

  // Load events when window opens
  useEffect(() => {
    if (isOpen) {
      loadEvents();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-2 md:p-4">
      <GlassPanel className="w-full max-w-2xl md:max-w-5xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 md:p-4 border-b border-jarvis-cyan/20">
          <div className="flex items-center gap-2 min-w-0">
            <JarvisButton size="icon" onClick={onClose} variant="ghost" className="flex-shrink-0">
              <ArrowLeft size={18} />
            </JarvisButton>
            <h2 className="text-lg md:text-xl font-orbitron text-jarvis-cyan truncate">Temporal Schedule</h2>
          </div>
          <JarvisButton
            size="icon"
            onClick={() => setShowForm(!showForm)}
            variant="default"
            className="flex-shrink-0"
          >
            <Plus size={18} />
          </JarvisButton>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden p-3 md:p-4 gap-3 md:gap-4">
          {/* Calendar */}
          <div className="flex-1 overflow-hidden min-h-0">
            {isLoading ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>Loading calendar...</p>
              </div>
            ) : (
              <CalendarView />
            )}
          </div>

          {/* New Event Form */}
          {showForm && (
            <div className="border-t border-jarvis-cyan/20 pt-3 md:pt-4 space-y-2 md:space-y-3 max-h-48 overflow-y-auto">
              <div className="grid grid-cols-2 gap-2 md:gap-3">
                <Input
                  placeholder="Event title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="bg-black/20 border-jarvis-cyan/30 text-jarvis-cyan placeholder:text-muted-foreground text-sm"
                />
                <Select value={formData.type} onValueChange={(val) => setFormData({ ...formData, type: val as EventType })}>
                  <SelectTrigger className="bg-black/20 border-jarvis-cyan/30 text-sm">
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={EventType.TASK}>Task</SelectItem>
                    <SelectItem value={EventType.MEETING}>Meeting</SelectItem>
                    <SelectItem value={EventType.REMINDER}>Reminder</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-2 md:gap-3">
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="bg-black/20 border-jarvis-cyan/30 text-jarvis-cyan text-sm"
                />
                <Input
                  type="time"
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                  className="bg-black/20 border-jarvis-cyan/30 text-jarvis-cyan text-sm"
                />
              </div>

              <Textarea
                placeholder="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="bg-black/20 border-jarvis-cyan/30 text-foreground placeholder:text-muted-foreground resize-none text-sm h-16"
              />

              <div className="flex gap-2 justify-end flex-wrap md:flex-nowrap">
                <JarvisButton
                  onClick={() => setShowForm(false)}
                  variant="ghost"
                  className="text-sm"
                >
                  Cancel
                </JarvisButton>
                <JarvisButton onClick={createEvent} variant="default" className="gap-2 text-sm">
                  <Save size={16} />
                  <span className="hidden md:inline">Create</span>
                </JarvisButton>
              </div>
            </div>
          )}
        </div>
      </GlassPanel>
    </div>
  );
};
