import { useState, useEffect, useCallback } from 'react';
import { GlassPanel } from './ui/GlassPanel';
import { JarvisButton } from './ui/JarvisButton';
import { Switch } from './ui/switch';
import { Communication } from '@/lib/client_websocket';
import { toast } from 'sonner';
import { ArrowLeft, ArrowRight, Edit, Plus } from 'lucide-react';
import { JarvisInput } from './ui/JarvisInput';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { FaceRecognition } from './FaceRecognition';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'


interface SettingsWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onUseVideoChange?: (useVideo: boolean) => void;
  currentUseVideo?: boolean;
  onCityChange?: (city: string) => void;
  currentCity?: string;
  
}

interface AppSettings {
  useVideo: boolean;
  city: string;
  use24hrFormat: boolean;
  useFaceRecognition: boolean;
  
}
export enum TaskType {
  TASK = "Task",
  MEETING = "Meeting",
  REMINDER = "Reminder"
}
type Event = {
  id: string | null;
  name: string;
  description: string;
  time: string; // In 24-hour format HH:MM
  date: string; // In YYYY-MM-DD format
  type: TaskType;
};


export const SettingsWindow = ({
   isOpen, onClose, onUseVideoChange, currentUseVideo, 
   onCityChange, currentCity }: SettingsWindowProps) => {
  const [settings, setSettings] = useState<AppSettings>({ useVideo: currentUseVideo || false, 
    city: currentCity || 'New York', use24hrFormat: false, useFaceRecognition: false });
  const [isLoading, setIsLoading] = useState(true);
  const [isWeatherOpen, setIsWeatherOpen] = useState(false);
  const [addEvent, setAddEvent] = useState<boolean>(false);
  const [events, setEvents] = useState<Event[]>([]);
  const [isEventsOpen, setIsEventsOpen] = useState(false);
  const [isEditEventOpen, setIsEditEventOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isFaceRecognitionOpen, setIsFaceRecognitionOpen] = useState(true);
  // Confirmation dialog states
  const [confirmDelete, setConfirmDelete] = useState<{open: boolean, eventId: string | null}>({open: false, eventId: null});
  const [confirmUpdate, setConfirmUpdate] = useState<{open: boolean}>({open: false});
  
  // State for new event form
  const [newEvent, setNewEvent] = useState({
    name: '',
    description: '',
    time: '',
    type: '',
    date: '',
  });
  
  // Load events from database via websocket
  const loadEvents = async () => {
    try {
      setIsLoading(true);
      // Send a message to the server to get events
      Communication.sendMessage(JSON.stringify({ 
        type: 'get_events',
        request_id: 'load_events'
      }));
      
      // Set up a temporary listener for the response
      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'load_events' && data.type === 'events_response') {
            setEvents(data.payload?.events || []);
            off(); // Remove the listener after receiving the response
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
  
  // Save event to database via websocket
  const saveEvent = async (eventData: any) => {
    try {
      // Format the event data with UTC datetime
      const formattedEventData = {
        ...eventData,
        dateTime: convertToUTC(eventData.date, eventData.time)
      };
      
      // Send a message to the server to save the event
      Communication.sendMessage(JSON.stringify({ 
        type: 'save_event',
        request_id: 'save_event_' + Date.now(),
        payload: formattedEventData
      }));
      
      // Refresh events after saving
      setTimeout(() => loadEvents(), 500);
    } catch (error) {
      console.error('Error saving event:', error);
      toast.error('Failed to save event');
    }
  };
  
  // Update event in database via websocket
  const updateEvent = async (eventData: any) => {
    try {
      // Format the event data with UTC datetime
      const formattedEventData = {
        ...eventData,
        dateTime: convertToUTC(eventData.date, eventData.time)
      };
      
      // Send a message to the server to update the event
      Communication.sendMessage(JSON.stringify({ 
        type: 'update_event',
        request_id: 'update_event_' + Date.now(),
        payload: formattedEventData
      }));
      
      // Refresh events after updating
      setTimeout(() => loadEvents(), 500);
    } catch (error) {
      console.error('Error updating event:', error);
      toast.error('Failed to update event');
    }
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (addEvent){
      if (!newEvent.name || !newEvent.time) {
        toast.error('Name and time are required');
        return;
      }
      
      const eventToSave = {
        id: Date.now().toString(),
        name: newEvent.name,
        description: newEvent.description,
        time: newEvent.time,
        type: newEvent.type,
      };
      
      saveEvent(eventToSave);
      setNewEvent({ name: '', description: '', time: '', type: '', date: '' });
      setAddEvent(false);
      toast.success('Event created successfully');
    }
    else if (isEditEventOpen && selectedEvent){
      setConfirmUpdate({open: true});
    }
  };
  
  const handleTaskChange = (value: TaskType) => {
    if (addEvent){
      setNewEvent(prev => ({
        ...prev,
        type: value
      }));
    }
    else if (isEditEventOpen && selectedEvent){
      setSelectedEvent(prev => ({
        ...prev,
        type: value
      }));
    }
  };
  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    if (addEvent){
      setNewEvent(prev => ({
      ...prev,
      [name]: value
    }));
    }
    else{
    setSelectedEvent(prev => ({
      ...prev,
      [name]: value
    }));
  };
  };
  
  // Convert local date and time to UTC ISO string
  const convertToUTC = (dateStr: string, timeStr: string): string => {
    if (!dateStr || !timeStr) return '';
    
    // Create a Date object from date and time
    const localDate = new Date(`${dateStr}T${timeStr}`);
    
    // Convert to UTC by adjusting for timezone offset
    const utcDate = new Date(localDate.getTime() + localDate.getTimezoneOffset() * 60000);
    
    // Format as ISO string but return only the date and time part
    return utcDate.toISOString().slice(0, 16);
  };
  
  // Format event data for sending to WebSocket
  const formatEventData = (event: any) => {
    const { date, time, ...rest } = event;
    return {
      ...rest,
      dateTime: convertToUTC(date, time) // Send as combined UTC timestamp
    };
  };
  
  // Delete event from database via websocket
  const handleDeleteEvent = async (eventId: string) => {
    setConfirmDelete({open: true, eventId});
  };
  
  // Confirm delete event
  const confirmDeleteEvent = async () => {
    if (confirmDelete.eventId) {
      try {
        // Send a message to the server to delete the event
        Communication.sendMessage(JSON.stringify({ 
          type: 'delete_event',
          request_id: 'delete_event_' + Date.now(),
          payload: { id: confirmDelete.eventId }
        }));
        
        // Refresh events after deletion
        setTimeout(() => loadEvents(), 500);
        toast.success('Event deleted successfully');
      } catch (error) {
        console.error('Error deleting event:', error);
        toast.error('Failed to delete event');
      } finally {
        setConfirmDelete({open: false, eventId: null});
      }
    }
  };
  
  // Confirm update event
  const confirmUpdateEvent = async () => {
    if (isEditEventOpen && selectedEvent) {
      try {
        updateEvent(selectedEvent);
        setNewEvent({ name: '', description: '', time: '', type: '', date: '' });
        setIsEditEventOpen(false);
        setSelectedEvent(null);
        toast.success('Event updated successfully');
      } catch (error) {
        console.error('Error updating event:', error);
        toast.error('Failed to update event');
      } finally {
        setConfirmUpdate({open: false});
      }
    }
  };
  
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  // Load settings from database via websocket
  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);
  
  // Load events when events section is opened
  useEffect(() => {
    if (isEventsOpen) {
      loadEvents();
    }
  }, [isEventsOpen]);

    const loadSettings = async () => {
      try {
        setIsLoading(true);
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
              setSettings({
                useVideo: data.payload?.useVideo ?? false,
                city: data.payload?.city ?? 'New York',
                use24hrFormat: data.payload?.use24hrFormat ?? false,
                useFaceRecognition: data.payload?.useFaceRecognition ?? false
              });
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
        setIsLoading(false);
      }
    };
  
  const saveSettings = async (newSettings: AppSettings) => {
    try {
      // Send settings to server to save in database
      Communication.sendMessage(JSON.stringify({ 
        type: 'save_settings',
        payload: newSettings,
        request_id: 'save_settings'
      }));
      
      // Set up a temporary listener for the save response
      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'save_settings' && data.type === 'save_settings_response') {
            if (data.success) {
              toast.success('Settings saved successfully');
              setSettings(newSettings);
            } else {
              toast.error(data.error || 'Failed to save settings');
            }
            off(); // Remove the listener after receiving the response
          }
        } catch (e) {
          console.error('Error parsing save settings response:', e);
        }
      });
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('Failed to save settings');
    }
  };

  const handleUseVideoChange = (checked: boolean) => {
    const newSettings = { ...settings, useVideo: checked };
    setSettings(newSettings);
    onUseVideoChange?.(checked);
    saveSettings(newSettings);
  };
  const handle24hrFormatChange = (checked: boolean) => {
    const newSettings = { ...settings, use24hrFormat: checked };
    setSettings(newSettings);
    saveSettings(newSettings);
  };
  const handleFaceRecognitionChange = (checked: boolean) => {
    const newSettings = { ...settings, useFaceRecognition: checked };
    setSettings(newSettings);
    saveSettings(newSettings);
    setIsFaceRecognitionOpen(checked);
  };
  
  // Debounced search function to avoid too many API calls
  const debouncedSearch = useCallback(
    debounce(async (searchTerm: string) => {
      if (searchTerm.length < 2) {
        setSearchResults([]);
        setIsSearching(false);
        return;
      }
      
      try {
        setIsSearching(true);
        const response = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(searchTerm)}&count=10&language=en&format=json`
        );
        
        if (!response.ok) {
          throw new Error('Search failed');
        }
        
        const data = await response.json();
        if (data.results) {
          setSearchResults(data.results);
        } else {
          setSearchResults([]);
        }
      } catch (error) {
        console.error('Error searching cities:', error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 500),
    []
  );
  
  // Handle city input change
  const handleCityInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSettings({ ...settings, city: value });
    
    // Trigger debounced search
    debouncedSearch(value);
  };
  
  // Simple debounce utility function
  function debounce<T extends (...args: any[]) => any>(func: T, wait: number) {
    let timeout: NodeJS.Timeout;
    return function executedFunction(...args: Parameters<T>): void {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <GlassPanel className="pointer-events-auto w-full max-w-md p-6 relative">
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-orbitron text-lg text-primary tracking-wider">System Settings</h2>
          <JarvisButton 
            variant="ghost" 
            size="icon"
            onClick={onClose}
            className="text-primary hover:bg-primary/10"
          >
            ×
          </JarvisButton>
        </div>
        
        {isWeatherOpen && (
          <div className="space-y-4">
            <div className="flex items-center">
              <JarvisButton 
                variant="ghost" 
                size="icon"
                onClick={() => setIsWeatherOpen(false)}
                className="text-primary hover:bg-primary/10"
              >
                <ArrowLeft size={16} className="text-muted-foreground" />
              </JarvisButton>
            </div>
            <div className="space-y-4">
              <div>
                <JarvisInput
                  type="text"
                  className="w-full p-2 rounded-md border border-input bg-background shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="Search the city or region of your choice"
                  value={settings.city}
                  onChange={handleCityInputChange}
                  style={{ width: '100%', maxWidth: '100%' }}                  
                />
              </div>
              
              {/* Popular Global Cities */}
              <div className="space-y-2">
                <h4 className="font-orbitron text-sm text-primary tracking-wider">Popular Global Cities</h4>
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                  {[
                    'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
                    'London', 'Birmingham', 'Manchester', 'Glasgow', 'Liverpool',
                    'Tokyo', 'Osaka', 'Kyoto', 'Yokohama', 'Nagoya',
                    'Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice',
                    'Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide',
                    'Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Al Ain',
                    'Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Tianjin',
                    'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Ahmedabad',
                    'São Paulo', 'Rio de Janeiro', 'Brasília', 'Salvador', 'Fortaleza',
                    'Moscow', 'Saint Petersburg', 'Novosibirsk', 'Yekaterinburg', 'Kazan',
                    'Berlin', 'Hamburg', 'Munich', 'Cologne', 'Frankfurt',
                    'Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Edmonton',
                    'Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon'
                  ].map((city) => (
                    <JarvisButton
                      key={city}
                      variant="outline"
                      className="text-xs p-2 h-auto truncate"
                      onClick={() => {
                        const newSettings = { ...settings, city };
                        setSettings(newSettings);
                        saveSettings(newSettings);
                        onCityChange?.(city);
                        setIsWeatherOpen(false);
                        toast.success(`Weather city set to ${city}`);
                      }}
                    >
                      {city}
                    </JarvisButton>
                  ))}
                </div>
              </div>
              
              {/* Search results - dynamically fetched from geocoding API */}
              <div className="space-y-2">
                <h4 className="font-orbitron text-sm text-primary tracking-wider">Search Results</h4>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {isSearching ? (
                    <div className="text-xs text-muted-foreground text-center py-2">
                      Searching...
                    </div>
                  ) : searchResults.length > 0 ? (
                    searchResults.map((result: any) => (
                      <JarvisButton
                        key={result.id}
                        variant="ghost"
                        className="w-full text-left justify-start text-sm p-2 h-auto"
                        onClick={() => {
                          const newSettings = { ...settings, city: result.name };
                          setSettings(newSettings);
                          saveSettings(newSettings);
                          onCityChange?.(result.name);
                          setIsWeatherOpen(false);
                          toast.success(`Weather city set to ${result.name}`);
                        }}
                      >
                        <div>
                          <div className="font-medium">{result.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {result.admin1 ? `${result.admin1}, ` : ''}{result.country}
                          </div>
                        </div>
                      </JarvisButton>
                    ))
                  ) : settings.city && settings.city.length > 1 ? (
                    <div className="text-xs text-muted-foreground text-center py-2">
                      No results found for "{settings.city}". Try another search.
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground text-center py-2">Enter at least 2 characters to search</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        {isEventsOpen && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
              <JarvisButton 
                variant="ghost" 
                size="icon"
                onClick={() => setIsEventsOpen(false)}
                className="text-primary hover:bg-primary/10"
              >
                <ArrowLeft size={16} className="text-muted-foreground" />
              </JarvisButton>
            </div>
            <div className="flex items-center">
              <JarvisButton 
                variant="ghost" 
                size="icon"
                onClick={() => setAddEvent(true)}
                className="text-primary hover:bg-primary/10"
              >
                <Plus size={16} className="text-muted-foreground" />
              </JarvisButton>
            </div>
            </div>
            
            {/* Events List */}
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {events.length > 0 ? (
                events.map((event) => (
                  <div key={event.id} className="p-3 bg-jarvis-dark/30 rounded-lg border border-jarvis-cyan/20">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-orbitron text-sm text-primary">{event.name}</h4>
                        <p className="text-xs text-muted-foreground mt-1">{event.description}</p>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(event.date + ' ' + event.time).toLocaleString('en-US', {  dateStyle: 'short', timeStyle: 'short' })}
                      </div>
                      <div className="flex space-x-1">
                        <JarvisButton variant="ghost" size="icon" onClick={() => {
                          setSelectedEvent(event);
                          setIsEditEventOpen(true);
                        }}>
                          <Edit size={16} className="text-muted-foreground" />
                        </JarvisButton>
                        <JarvisButton 
                          variant="ghost" 
                          size="icon" 
                          onClick={() => handleDeleteEvent(event.id)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M3 6h18"></path>
                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                          </svg>
                        </JarvisButton>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No events scheduled
                </div>
              )}
            </div>
          </div>
        )}
        {isFaceRecognitionOpen && (
            <div className="pt-2">
              <JarvisButton size="icon" variant='ghost' onClick={() => setIsFaceRecognitionOpen(!isFaceRecognitionOpen)}>
                <ArrowLeft size={16}/>
              </JarvisButton>
              <div className="flex items-center justify-between">
            <div>
              <h3 className="font-orbitron text-sm text-primary tracking-wider">Use Face Recognition</h3>
              <p className="text-xs text-muted-foreground">Enable or disable face recognition</p>
            </div>
            <Switch
              checked={settings.useFaceRecognition}
              onCheckedChange={handleFaceRecognitionChange}
              disabled={isLoading}
            />
          </div>
              <FaceRecognition />
            </div>
          )}
        {selectedEvent && (
        <Dialog open={isEditEventOpen} onOpenChange={setIsEditEventOpen}>
          <DialogContent className="glass-panel border-jarvis-cyan/30 max-w-md">
            <DialogHeader>
              <DialogTitle className="text-primary font-orbitron">Edit Event {selectedEvent?.name}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-primary">Event Name</Label>
                  <Input
                    id="name"
                    name="name"
                    value={selectedEvent.name}
                    onChange={handleInputChange}
                    placeholder="Enter event name"
                    className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="date" className="text-primary">Event Date</Label>
                    <Input
                      id="date"
                      name="date"
                      type="date"
                      value={selectedEvent.date}
                      onChange={handleInputChange}
                      className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="time" className="text-primary">Event Time</Label>
                    <Input
                      id="time"
                      name="time"
                      type="time"
                      value={selectedEvent.time}
                      onChange={handleInputChange}
                      className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description" className="text-primary">Description</Label>
                  <Textarea
                    id="description"
                    name="description"
                    value={selectedEvent.description}
                    onChange={handleInputChange}
                    placeholder="Enter event description"
                    className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary min-h-[80px]"
                  />
                </div>
                <div className='space-y-2'>
                  <Label htmlFor="type" className="text-primary">Event Type <span className="text-red-500">*</span></Label>
                  
                  <Select value={selectedEvent.type} onValueChange={(value) => handleTaskChange(value as TaskType)}>
                    <SelectTrigger className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary" 
                    value={selectedEvent.type}>
                      <SelectValue placeholder="Select a type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="task">Task</SelectItem>
                      <SelectItem value="meeting">Meeting</SelectItem>
                      <SelectItem value="reminder">Reminder</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsEditEventOpen(false)} className="border-jarvis-cyan/30 text-primary">
                  Cancel
                </Button>
                <Button type="submit" className="bg-jarvis-cyan/20 hover:bg-jarvis-cyan/30 text-primary">
                  Edit Event
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
        )}
        {/* Add Event Dialog */}
        <Dialog open={addEvent} onOpenChange={setAddEvent}>
          <DialogContent className="glass-panel border-jarvis-cyan/30 max-w-md">
            <DialogHeader>
              <DialogTitle className="text-primary font-orbitron">Add New Event</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-primary">Event Name <span className="text-red-500">*</span></Label>
                  <Input
                    id="name"
                    name="name"
                    value={newEvent.name}
                    onChange={handleInputChange}
                    placeholder="Enter event name"
                    className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="date" className="text-primary">Event Date <span className="text-red-500">*</span></Label>
                    <Input
                      id="date"
                      name="date"
                      type="date"
                      value={newEvent.date}
                      onChange={handleInputChange}
                      className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="time" className="text-primary">Event Time <span className="text-red-500">*</span></Label>
                    <Input
                      id="time"
                      name="time"
                      type="time"
                      value={newEvent.time}
                      onChange={handleInputChange}
                      className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                      required
                    />
                  </div>
                </div>
                <div className='space-y-2'>
                  <Label htmlFor="type" className="text-primary">Event Type <span className="text-red-500">*</span></Label>
                  <Select value={newEvent.type} onValueChange={(value) => handleTaskChange(value as TaskType)}>
                    <SelectTrigger className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary">
                      <SelectValue placeholder="Select a type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="task">Task</SelectItem>
                      <SelectItem value="meeting">Meeting</SelectItem>
                      <SelectItem value="reminder">Reminder</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description" className="text-primary">Description <span className="text-red-500">*</span></Label>
                  <Textarea
                    id="description"
                    name="description"
                    value={newEvent.description}
                    onChange={handleInputChange}
                    placeholder="Enter event description"
                    className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary min-h-[80px]"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setAddEvent(false)} className="border-jarvis-cyan/30 text-primary">
                  Cancel
                </Button>
                <Button type="submit" className="bg-jarvis-cyan/20 hover:bg-jarvis-cyan/30 text-primary">
                  Add Event
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
        {!isWeatherOpen && !isEventsOpen && !isFaceRecognitionOpen && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-orbitron text-sm text-primary tracking-wider">Use Video</h3>
              <p className="text-xs text-muted-foreground">Show or hide the video panel</p>
            </div>
            <Switch
              checked={settings.useVideo}
              onCheckedChange={handleUseVideoChange}
              disabled={isLoading}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-orbitron text-sm text-primary tracking-wider">Use 24 hrs format</h3>
              <p className="text-xs text-muted-foreground">Show the time in 24 hrs format</p>
            </div>
            <Switch
              checked={settings.use24hrFormat}
              onCheckedChange={handle24hrFormatChange}
              disabled={isLoading}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-orbitron text-sm text-primary tracking-wider">Weather</h3>
              <p className="text-xs text-muted-foreground">Change the city for weather updates</p>
            </div>
            <ArrowRight size={16} className="text-muted-foreground" onClick={() => setIsWeatherOpen(true)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-orbitron text-sm text-primary tracking-wider">Events</h3>
              <p className="text-xs text-muted-foreground">Add, remove or configure events</p>
            </div>
            <ArrowRight size={16} className="text-muted-foreground" onClick={() => setIsEventsOpen(true)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <JarvisButton variant='ghost' onClick={() => setIsFaceRecognitionOpen(!isFaceRecognitionOpen)} 
                value={isFaceRecognitionOpen ? 'On' : 'Off'}
                >
                Use Face Recognition
              </JarvisButton>
            </div>
            <Switch
              checked={settings.useFaceRecognition}
              onCheckedChange={handleFaceRecognitionChange}
              disabled={isLoading}
            />
          </div>
        </div>
        )}
        {/* Delete Confirmation Dialog */}
        <AlertDialog open={confirmDelete.open} onOpenChange={(open) => setConfirmDelete({open, eventId: confirmDelete.eventId})}>
          <AlertDialogContent className="glass-panel border-jarvis-cyan/30">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-primary">Confirm Delete</AlertDialogTitle>
              <AlertDialogDescription className="text-muted-foreground">
                Are you sure you want to delete this event? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setConfirmDelete({open: false, eventId: null})} className="border-jarvis-cyan/30 text-primary">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction onClick={confirmDeleteEvent} className="bg-red-500 hover:bg-red-600 text-white">
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
        
        {/* Update Confirmation Dialog */}
        <AlertDialog open={confirmUpdate.open} onOpenChange={(open) => setConfirmUpdate({open})}>
          <AlertDialogContent className="glass-panel border-jarvis-cyan/30">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-primary">Confirm Update</AlertDialogTitle>
              <AlertDialogDescription className="text-muted-foreground">
                Are you sure you want to update this event? Changes will be saved permanently.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setConfirmUpdate({open: false})} className="border-jarvis-cyan/30 text-primary">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction onClick={confirmUpdateEvent} className="bg-jarvis-cyan/20 hover:bg-jarvis-cyan/30 text-primary">
                Update
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </GlassPanel>
    </div>
  );
};
