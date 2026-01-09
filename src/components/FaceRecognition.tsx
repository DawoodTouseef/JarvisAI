import { useState, useRef, useEffect } from 'react';
import { Camera, Upload, X, User, Trash2, Save } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { JarvisButton } from '@/components/ui/JarvisButton';
import { toast } from 'sonner';
import { Communication } from '@/lib/client_websocket';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface FaceModel {
  id: string;
  name: string;
  filename: string;
  filepath: string;
  uploaded_at: string;
  isActive: boolean;
}

export const FaceRecognition = () => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [personName, setPersonName] = useState('');
  const [savedModels, setSavedModels] = useState<FaceModel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCountingDown, setIsCountingDown] = useState(false);
  const [countdown, setCountdown] = useState(3);
  
  // Dialog states
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogImageData, setDialogImageData] = useState<string | null>(null);
  const [command, setCommand] = useState('');
  const [description, setDescription] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load saved face models
  useEffect(() => {
    loadFaceModels();
    
    // Cleanup function when component unmounts
    return () => {
      if (isCameraOpen) {
        stopCamera();
      }
    };
  }, []);

  const loadFaceModels = async () => {
    try {
      setIsLoading(true);
      Communication.sendMessage(JSON.stringify({
        type: 'face_recognition',
        action: 'get_models',
        request_id: 'load_face_models'
      }));

      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id === 'load_face_models' && data.type === 'face_recognition_models_response') {
            setSavedModels(data.payload?.models || []);
            off();
          }
        } catch (e) {
          console.error('Error parsing face models response:', e);
        }
      });
    } catch (error) {
      console.error('Error loading face models:', error);
      toast.error('Failed to load face recognition models');
    } finally {
      setIsLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      console.log('Attempting to start camera...');
      setIsLoading(true);
      
      // Request camera access with simplified constraints
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: true,
      });
      
      
      if (videoRef.current) {
          videoRef.current.srcObject = stream;
          
          // Ensure the video plays properly
          videoRef.current.muted = true;
          videoRef.current.autoplay = true;
          videoRef.current.playsInline = true;
          
          // Wait for video to load metadata to ensure proper playback
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(e => console.error("Error playing video:", e));
          };
        }
    } catch (error: any) {
      console.error('Error accessing camera:', error);
      setIsLoading(false);
      
      // Provide specific error messages
      if (error.name === 'NotAllowedError') {
        toast.error('Camera access denied. Please allow camera permissions in your browser settings.');
      } else if (error.name === 'NotFoundError') {
        toast.error('No camera found. Please connect a camera and try again.');
      } else if (error.name === 'NotReadableError') {
        toast.error('Camera is already in use by another application.');
      } else {
        toast.error(`Could not access camera: ${error.message || 'Unknown error'}. Please check permissions and ensure you are using HTTPS or localhost.`);
      }
    }
  };

  const stopCamera = () => {
    console.log('Stopping camera...');
    
    if (videoRef.current) {
      // Remove all event listeners
      videoRef.current.onloadedmetadata = null;
      videoRef.current.onplaying = null;
      videoRef.current.onerror = null;
      
      // Stop all tracks
      if (videoRef.current.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach(track => {
          console.log('Stopping track:', track.kind);
          track.stop();
        });
        videoRef.current.srcObject = null;
      }
      
      // Pause the video element
      videoRef.current.pause();
    }
    
    setIsCameraOpen(false);
    setCapturedImage(null);
    setIsCountingDown(false);
    setCountdown(3);
    setIsLoading(false);
    
    console.log('Camera stopped successfully');
  };

  const startCountdown = () => {
    console.log('Starting countdown...');
    
    // Validate camera is ready
    if (!videoRef.current || !isCameraOpen) {
      console.error('Camera not ready for countdown');
      toast.error('Camera not ready. Please start camera first.');
      return;
    }
    
    setIsCountingDown(true);
    setCountdown(3);
    
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        console.log('Countdown:', prev);
        if (prev <= 1) {
          clearInterval(countdownInterval);
          console.log('Calling captureImage...');
          captureImage();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const captureImage = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      
      // Check if video is ready and has valid dimensions
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        console.error('Video not ready or has invalid dimensions');
        toast.error('Camera not ready. Please try again.');
        setIsCountingDown(false);
        setCountdown(3);
        return;
      }
      
      const context = canvas.getContext('2d');

      if (context) {
        try {
          // Set canvas dimensions to match video
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          
          // Clear canvas first
          context.clearRect(0, 0, canvas.width, canvas.height);
          
          // Draw video frame to canvas
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          
          // Convert to data URL
          const imageData = canvas.toDataURL('image/jpeg', 0.9);
          
          // Validate that we actually captured something
          if (imageData && imageData.length > 1000) { // Basic validation
            // Open dialog with captured image instead of setting directly
            setDialogImageData(imageData);
            setIsDialogOpen(true);
            console.log('Image captured successfully - opening dialog');
          } else {
            console.error('Failed to capture valid image');
            toast.error('Failed to capture image. Please try again.');
            setIsCountingDown(false);
            setCountdown(3);
            return;
          }
          
          // Stop camera after capture
          stopCamera();
        } catch (error) {
          console.error('Error during image capture:', error);
          toast.error('Capture failed. Please try again.');
          setIsCountingDown(false);
          setCountdown(3);
        }
      } else {
        console.error('Could not get canvas context');
        toast.error('Canvas not available. Please try again.');
        setIsCountingDown(false);
        setCountdown(3);
      }
    } else {
      console.error('Video or canvas reference is null');
      toast.error('Camera not initialized properly. Please restart.');
      setIsCountingDown(false);
      setCountdown(3);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        // Open dialog with uploaded image instead of setting directly
        setDialogImageData(e.target?.result as string);
        setIsDialogOpen(true);
        toast.success('Image uploaded! Please enter details in the dialog.');
      };
      reader.readAsDataURL(file);
    }
  };

  const saveFaceModel = async () => {
    if (!capturedImage || !personName.trim()) {
      toast.error('Please capture an image and enter a name');
      return;
    }

    try {
      setIsLoading(true);
      
      // Extract base64 data
      const base64Data = capturedImage.split(',')[1];
      const binaryData = atob(base64Data);
      const bytes = new Uint8Array(binaryData.length);
      for (let i = 0; i < binaryData.length; i++) {
        bytes[i] = binaryData.charCodeAt(i);
      }

      // Create WebSocket for face recognition upload
      // TEMPORARY: Force localhost for testing
      const selectedServer = 'http://localhost:8000'; // localStorage.getItem('jarvis:selectedServer');
      const baseUrl = selectedServer || 'http://localhost:8000';
      const wsUrl = baseUrl.replace(/^http/, 'ws') + '/face_recognition';
      
      console.log('Face recognition WebSocket URL:', wsUrl);
      console.log('Selected server from localStorage:', selectedServer);
      console.log('Base URL used:', baseUrl);
      
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        // Send metadata first
        const metadata = {
          type: 'face_recognition',
          action: 'save_model',
          payload: {
            name: personName.trim(),
            extension: '.jpg'
          },
          request_id: 'save_face_model_' + Date.now()
        };
        ws.send(JSON.stringify(metadata));
        
        // Send binary image data
        ws.send(bytes.buffer);
      };

      ws.onmessage = (event) => {
        try {
          const response = JSON.parse(event.data);
          if (response.request_id?.startsWith('save_face_model_')) {
            if (response.type === 'face_recognition_save_response') {
              if (response.success) {
                toast.success(`Face model for "${personName}" saved successfully`);
                setCapturedImage(null);
                setPersonName('');
                loadFaceModels(); // Refresh the list
              } else {
                toast.error(response.error || 'Failed to save face model');
              }
              ws.close();
            }
          }
        } catch (e) {
          console.error('Error parsing save response:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        console.error('Failed to connect to:', wsUrl);
        toast.error(`Connection failed to ${wsUrl}. Please check if the server is running.`);
        ws.close();
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        if (event.code !== 1000) { // Not normal closure
          toast.error(`Connection closed unexpectedly. Code: ${event.code}`);
        }
      };
      
      // Timeout for connection
      setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.error('WebSocket connection timeout');
          toast.error('Connection timeout. Please check server availability.');
          ws.close();
        }
      }, 5000);

    } catch (error) {
      console.error('Error saving face model:', error);
      toast.error('Failed to save face model');
    } finally {
      setIsLoading(false);
    }
  };

  const deleteFaceModel = async (modelId: string, modelName: string) => {
    try {
      setIsLoading(true);
      toast.info(`Deleting face model "${modelName}"...`);
      
      Communication.sendMessage(JSON.stringify({
        type: 'face_recognition',
        action: 'delete_model',
        request_id: 'delete_face_model_' + Date.now(),
        payload: { id: modelId }
      }));

      const off = Communication.onMessage((msg) => {
        try {
          const data = JSON.parse(msg);
          if (data.request_id.startsWith('delete_face_model_') && data.type === 'face_recognition_delete_response') {
            if (data.success) {
              toast.success(`Face model "${modelName}" and associated image file deleted successfully`);
              loadFaceModels(); // Refresh the list
            } else {
              toast.error(data.error || 'Failed to delete face model');
            }
            off();
          }
        } catch (e) {
          console.error('Error parsing delete response:', e);
          toast.error('Error processing delete response');
        }
      });
    } catch (error) {
      console.error('Error deleting face model:', error);
      toast.error('Failed to delete face model');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">

      {/* Image Capture Section */}
      <GlassPanel className="p-6">
        <h4 className="font-orbitron text-md text-primary mb-4">Add New Face Model</h4>
        
        {!capturedImage ? (
          <div className="space-y-4">
            <div className="flex gap-4">
              <JarvisButton 
                onClick={startCamera}
                disabled={isCameraOpen || isLoading}
                className="flex items-center gap-2"
              >
                <Camera size={16} />
                Use Camera
              </JarvisButton>
              
              <JarvisButton 
                onClick={() => fileInputRef.current?.click()}
                disabled={isCameraOpen || isLoading}
                className="flex items-center gap-2"
              >
                <Upload size={16} />
                Upload Image
              </JarvisButton>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>

            {isCameraOpen && (
              <div className="relative">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  className="w-full max-w-md rounded-lg border border-jarvis-cyan/30"
                />
                <div className="flex gap-2 mt-2">
                  {!isCountingDown ? (
                    <>
                      <JarvisButton onClick={startCountdown} className="flex items-center gap-2">
                        <Camera size={16} />
                        Capture Photo
                      </JarvisButton>
                      {/* Debug button - remove in production */}
                      <JarvisButton 
                        onClick={captureImage} 
                        variant="outline" 
                        className="flex items-center gap-2"
                        disabled={!isCameraOpen}
                      >
                        <Camera size={16} />
                        Test Capture
                      </JarvisButton>
                      <JarvisButton onClick={stopCamera} variant="outline" className="flex items-center gap-2">
                        <X size={16} />
                        Cancel
                      </JarvisButton>
                    </>
                  ) : (
                    <div className="w-full flex flex-col items-center justify-center py-4">
                      <div className="text-6xl font-bold text-primary mb-2">
                        {countdown}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Photo will be taken in {countdown} seconds...
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
                placeholder="Enter person's name"
                className="flex-1 px-3 py-2 bg-jarvis-dark/30 border border-jarvis-cyan/30 rounded-md text-primary placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-jarvis-cyan/50"
                disabled={isLoading}
              />
              <JarvisButton 
                onClick={saveFaceModel}
                disabled={!personName.trim() || isLoading}
                className="flex items-center gap-2"
              >
                <Save size={16} />
                
              </JarvisButton>
              <JarvisButton 
                onClick={() => setCapturedImage(null)}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Camera size={16} />
              </JarvisButton>
            </div>
          </div>
        )}

        <canvas ref={canvasRef} className="hidden" />
      </GlassPanel>

      {/* Saved Models Section */}
      <GlassPanel className="p-6">
        <h4 className="font-orbitron text-md text-primary mb-4">Saved Face Models</h4>
        
        {isLoading ? (
          <div className="text-center py-4 text-muted-foreground">
            Loading face models...
          </div>
        ) : savedModels.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {savedModels.map((model) => (
              <div 
                key={model.id} 
                className="p-4 bg-jarvis-dark/30 rounded-lg border border-jarvis-cyan/20"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h5 className="font-orbitron text-sm text-primary">{model.name}</h5>
                    <p className="text-xs text-muted-foreground">
                      Added: {new Date(model.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                  <JarvisButton
                    onClick={() => deleteFaceModel(model.id, model.name)}
                    variant="ghost"
                    size="sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={isLoading}
                  >
                    <Trash2 size={14} />
                  </JarvisButton>
                </div>
                <div className="text-xs text-muted-foreground">
                  <p>File: {model.filename}</p>
                  <p>Status: {model.isActive ? 'Active' : 'Inactive'}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <User size={48} className="mx-auto mb-2 opacity-50" />
            <p>No face models saved yet</p>
            <p className="text-xs mt-1">Capture or upload images to get started</p>
          </div>
        )}
      </GlassPanel>
      
      {/* Image Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="glass-panel border-jarvis-cyan/30 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-primary font-orbitron">Image Details</DialogTitle>
          </DialogHeader>
          
          {dialogImageData && (
            <div className="mb-4">
              <img 
                src={dialogImageData} 
                alt="Captured face" 
                className="w-full h-48 object-cover rounded-lg border border-jarvis-cyan/30"
              />
            </div>
          )}
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="personName" className="text-primary">Person Name *</Label>
              <Input
                id="personName"
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
                placeholder="Enter person's name"
                className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="command" className="text-primary">Command</Label>
              <Input
                id="command"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="e.g., save, display image, etc."
                className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description" className="text-primary">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Additional notes about this face model..."
                className="bg-jarvis-dark/30 border-jarvis-cyan/30 text-primary min-h-[80px]"
              />
            </div>
          </div>
          
          <div className="flex gap-3 pt-4">
            <JarvisButton
              onClick={() => {
                // Cancel - close dialog and reset
                setIsDialogOpen(false);
                setDialogImageData(null);
                setPersonName('');
                setCommand('');
                setDescription('');
                setCapturedImage(null);
              }}
              variant="outline"
              className="flex-1 border-jarvis-cyan/30 text-primary"
            >
              Cancel
            </JarvisButton>
            <JarvisButton
              onClick={() => {
                // Save the face model
                if (dialogImageData && personName.trim()) {
                  setCapturedImage(dialogImageData);
                  saveFaceModel();
                  setIsDialogOpen(false);
                  setDialogImageData(null);
                  setCommand('');
                  setDescription('');
                } else {
                  toast.error('Please enter a person name');
                }
              }}
              disabled={!personName.trim() || isLoading}
              className="flex-1 bg-jarvis-cyan/20 hover:bg-jarvis-cyan/30 text-primary flex items-center gap-2"
            >
              <Save size={16} />
              Save Model
            </JarvisButton>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};