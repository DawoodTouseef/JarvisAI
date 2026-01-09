# Jarvis Console

An AI-powered console application inspired by JARVIS from Marvel's Iron Man, designed to provide an interactive, voice-controlled interface for managing tasks, accessing information, and controlling smart systems.

## Features

- **Voice Recognition**: Wake word detection ("Jarvis") with real-time audio processing
- **Interactive Dashboard**: Modern React-based UI with 3D visualizations and widgets
- **System Monitoring**: Real-time CPU, memory, GPU, and network stats
- **WebSocket Communication**: Bidirectional communication between frontend and backend
- **LLM Integration**: Support for various AI models via Ollama and OpenAI
- **Customizable Widgets**: Calendar, weather, news, and quick actions
- **Audio Visualization**: Real-time spectrum analysis for audio input

## Architecture

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with shadcn/ui components
- **3D Graphics**: Three.js with React Three Fiber
- **State Management**: Zustand
- **Audio Processing**: Web Audio API with WaveSurfer.js

### Backend
- **Framework**: FastAPI with WebSockets
- **Speech Recognition**: PocketSphinx for hotword detection
- **AI Integration**: Autogen agents, OpenAI API, Ollama
- **System Monitoring**: psutil, pynvml for hardware stats
- **Concurrency**: asyncio for async operations

## Installation

### Prerequisites
- Node.js 18+
- Python 3.8+
- Git
- For desktop builds: Electron and electron-builder
- For mobile builds: Android Studio (for Android), Xcode (for iOS)

### Frontend Setup

```bash
# Clone the repository
git clone <repository-url>
cd jarvis-console

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

```bash
# Navigate to server directory
cd server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

The backend API will be available at `http://localhost:8000`

## Building Cross-Platform Applications

This application can be built for multiple platforms using Electron (desktop) and Capacitor (mobile).

### Desktop Builds (Windows, Mac, Linux)

```bash
# Install dependencies
npm install

# Build the Python server executable
npm run build:server

# Build for specific platforms
npm run electron:build:win    # Windows
npm run electron:build:mac    # Mac
npm run electron:build:linux  # Linux

# Or build for all platforms
npm run electron:build
```

### Mobile Builds (iOS, Android)

For mobile, the backend server needs to be accessible over the network (run on a desktop machine).

```bash
# Install dependencies
npm install

# Sync web assets to mobile projects
npm run cap:sync

# Open in Android Studio
npm run cap:android

# Open in Xcode
npm run cap:ios
```

Note: For mobile apps, ensure the server is running on the same network and update the WebSocket URLs if needed.

## Development

### Project Structure

```
jarvis-console/
├── src/                    # Frontend source code
│   ├── components/         # React components
│   ├── pages/             # Application pages
│   ├── stores/            # Zustand state management
│   └── lib/               # Utilities and WebSocket client
├── server/                # Backend source code
│   ├── main.py           # FastAPI application
│   ├── connection_manager.py
│   └── worker/           # AI agents and LLM workers
├── discoveryserver/      # Service discovery
└── public/               # Static assets
```

### Running the Full Stack

```bash
# Start both frontend and backend concurrently
npm run dev
```

This runs the discovery server, frontend dev server, and backend simultaneously.

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Backend configuration
OPENAI_API_KEY=your_openai_key
OLLAMA_BASE_URL=http://localhost:11434

# Frontend configuration
VITE_WS_URL=ws://localhost:8000
```

## Contributing

We welcome contributions from developers of all skill levels! Here are ways you can help:

### Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/jarvis-console.git`
3. **Create a feature branch**: `git checkout -b feature/your-feature-name`
4. **Make your changes** and test thoroughly
5. **Commit your changes**: `git commit -m "Add your feature"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request** with a clear description

### Development Guidelines

- Follow TypeScript best practices
- Use ESLint and Prettier for code formatting
- Write meaningful commit messages
- Test your changes thoroughly
- Update documentation when adding new features

### Areas for Contribution

- **UI/UX Improvements**: Enhance the dashboard design and user experience
- **New Widgets**: Add calendar, weather, news, or custom widgets
- **AI Features**: Improve LLM integration, add new agents, or enhance speech recognition
- **Performance**: Optimize audio processing, reduce latency, improve resource usage
- **Accessibility**: Add keyboard navigation, screen reader support, and inclusive design
- **Testing**: Add unit tests, integration tests, and end-to-end tests
- **Documentation**: Improve setup guides, API docs, and user manuals

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers learn and contribute
- Follow security best practices

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Provide detailed steps to reproduce bugs
- Include environment information and screenshots when possible

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Inspired by JARVIS from Marvel's Iron Man series. Built with modern web technologies and AI frameworks.
