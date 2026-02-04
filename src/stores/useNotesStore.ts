import { create } from 'zustand';

export interface Note {
    id: string;
    title: string;
    content: string;
    createdAt: string;
    updatedAt: string;
}

interface NotesState {
    notes: Note[];
    setNotes: (notes: Note[]) => void;
    addNote: (note: Note) => void;
    updateNote: (id: string, note: Partial<Note>) => void;
    removeNote: (id: string) => void;
}

export const useNotesStore = create<NotesState>((set) => ({
    notes: [],
    setNotes: (notes) => set({ notes }),
    addNote: (note) => set((state) => ({ notes: [note, ...state.notes] })),
    updateNote: (id, updates) => set((state) => ({
        notes: state.notes.map((n) => n.id === id ? { ...n, ...updates } : n),
    })),
    removeNote: (id) => set((state) => ({
        notes: state.notes.filter((n) => n.id !== id),
    })),
}));
