import { useState, useEffect } from 'react';
import { GlassPanel } from './ui/GlassPanel';
import { JarvisButton } from './ui/JarvisButton';
import { Plus, Save, Trash2, ArrowLeft } from 'lucide-react';
import { Communication } from '@/lib/client_websocket';
import { useNotesStore } from '@/stores/useNotesStore';
import { toast } from 'sonner';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';

interface NotesWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotesWindow = ({ isOpen, onClose }: NotesWindowProps) => {
  const { notes, setNotes, addNote, updateNote, removeNote } = useNotesStore();
  const [activeNoteId, setActiveNoteId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');

  const activeNote = notes.find(n => n.id === activeNoteId);

  // Load notes from server via WebSocket
  const loadNotes = async () => {
    try {
      setIsLoading(true);
      Communication.sendMessage(JSON.stringify({
        type: 'get_notes',
        request_id: 'load_notes'
      }));

      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'load_notes' && data.type === 'notes_response') {
            setNotes(data.payload?.notes || []);
            off();
          }
        } catch (e) {
          console.error('Error parsing notes response:', e);
        }
      });
    } catch (error) {
      console.error('Error loading notes:', error);
      toast.error('Failed to load notes');
    } finally {
      setIsLoading(false);
    }
  };

  // Create new note
  const createNote = async () => {
    const newNote = {
      id: crypto.randomUUID(),
      title: 'Untitled Note',
      content: '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    try {
      Communication.sendMessage(JSON.stringify({
        type: 'save_note',
        request_id: `save_note_${Date.now()}`,
        payload: newNote
      }));

      addNote(newNote);
      setActiveNoteId(newNote.id);
      setEditTitle(newNote.title);
      setEditContent(newNote.content);
      toast.success('Note created');
    } catch (error) {
      console.error('Error creating note:', error);
      toast.error('Failed to create note');
    }
  };

  // Save note
  const saveNote = async () => {
    if (!activeNoteId || !activeNote) return;

    const updatedNote = {
      ...activeNote,
      title: editTitle || 'Untitled Note',
      content: editContent,
      updatedAt: new Date().toISOString(),
    };

    try {
      Communication.sendMessage(JSON.stringify({
        type: 'update_note',
        request_id: `update_note_${Date.now()}`,
        payload: updatedNote
      }));

      updateNote(activeNoteId, updatedNote);
      toast.success('Note saved');
    } catch (error) {
      console.error('Error saving note:', error);
      toast.error('Failed to save note');
    }
  };

  // Delete note
  const deleteNote = async (noteId: string) => {
    try {
      Communication.sendMessage(JSON.stringify({
        type: 'delete_note',
        request_id: `delete_note_${Date.now()}`,
        payload: { id: noteId }
      }));

      removeNote(noteId);
      if (activeNoteId === noteId) setActiveNoteId(null);
      toast.success('Note deleted');
    } catch (error) {
      console.error('Error deleting note:', error);
      toast.error('Failed to delete note');
    }
  };

  // Load notes when window opens
  useEffect(() => {
    if (isOpen) {
      loadNotes();
    }
  }, [isOpen]);

  // Update edit states when active note changes
  useEffect(() => {
    if (activeNote) {
      setEditTitle(activeNote.title);
      setEditContent(activeNote.content);
    }
  }, [activeNote]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-2 md:p-4">
      <GlassPanel className="w-full max-w-2xl md:max-w-4xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 md:p-4 border-b border-jarvis-cyan/20">
          <div className="flex items-center gap-2">
            <JarvisButton size="icon" onClick={onClose} variant="ghost">
              <ArrowLeft size={18} />
            </JarvisButton>
            <h2 className="text-lg md:text-xl font-orbitron text-jarvis-cyan">Data Logs</h2>
          </div>
          <JarvisButton size="icon" onClick={createNote} variant="default">
            <Plus size={18} />
          </JarvisButton>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col md:flex-row gap-3 md:gap-4 overflow-hidden p-3 md:p-4">
          {/* Notes List */}
          <div className="w-full md:w-56 md:overflow-y-auto space-y-2 mb-3 md:mb-0">
            {isLoading ? (
              <div className="text-center text-muted-foreground py-4">Loading notes...</div>
            ) : notes.length === 0 ? (
              <div className="text-center text-muted-foreground py-4">No notes yet</div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-1 gap-2">
                {notes.map(note => (
                  <div
                    key={note.id}
                    onClick={() => setActiveNoteId(note.id)}
                    className={`p-2 md:p-3 rounded-lg border cursor-pointer transition-all ${
                      activeNoteId === note.id
                        ? 'bg-jarvis-cyan/20 border-jarvis-cyan'
                        : 'bg-black/20 border-jarvis-cyan/30 hover:border-jarvis-cyan/50'
                    }`}
                  >
                    <p className="font-semibold text-xs md:text-sm text-jarvis-cyan truncate">{note.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{note.content.substring(0, 50)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Note Editor */}
          <div className="flex-1 flex flex-col gap-3 md:gap-4 overflow-hidden">
            {activeNote ? (
              <>
                <Input
                  placeholder="Note title"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="bg-black/20 border-jarvis-cyan/30 text-jarvis-cyan placeholder:text-muted-foreground text-sm"
                />
                <Textarea
                  placeholder="Start typing..."
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="flex-1 bg-black/20 border-jarvis-cyan/30 text-foreground placeholder:text-muted-foreground resize-none text-sm"
                />
                <div className="flex gap-2 justify-between flex-wrap md:flex-nowrap">
                  <JarvisButton
                    size="icon"
                    onClick={() => deleteNote(activeNoteId)}
                    variant="ghost"
                    className="text-red-500 hover:text-red-600"
                  >
                    <Trash2 size={18} />
                  </JarvisButton>
                  <JarvisButton onClick={saveNote} variant="default" className="gap-2 flex-1 md:flex-none text-sm">
                    <Save size={16} />
                    <span className="hidden md:inline">Save Note</span>
                  </JarvisButton>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p className="text-sm">Select a note or create a new one</p>
              </div>
            )}
          </div>
        </div>
      </GlassPanel>
    </div>
  );
};
