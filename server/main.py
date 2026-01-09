from fastapi import FastAPI,WebSocket,WebSocketDisconnect, APIRouter
from connection_manager import ConnectionManager
import psutil
import asyncio
import pynvml
import time
import pocketsphinx
from os.path import join as pathjoin
from settings import settings_manager
import json
from datetime import datetime
from deepface import DeepFace as df  
from pathlib import Path

JARVIS_DIR = Path(__file__).resolve().parent

# Create faces directory if it doesn't exist
faces_dir = JARVIS_DIR / "faces"

print("Creating faces directory if it doesn't exist...", faces_dir)
faces_dir.mkdir(parents=True, exist_ok=True)
app = FastAPI(
    title="Jarvis websocket server",
    lifespan=None,
    docs_url="/docs",
)


manager = ConnectionManager()

pynvml.nvmlInit()

MODEL_PATH = pocketsphinx.get_model_path()

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Check if the message is a settings-related request
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, dict):
                    message_type = parsed_data.get('type')
                    print(f"Received message type: {message_type}")
                    if message_type == 'get_settings':
                        # Return current settings
                        settings = settings_manager.get_settings()
                        response = {
                            'type': 'settings_response',
                            'request_id': parsed_data.get('request_id'),
                            'payload': settings
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        continue
                    elif message_type == 'save_settings':
                        # Save the new settings
                        new_settings = parsed_data.get('payload', {})
                        success = settings_manager.update_settings(new_settings)
                        response = {
                            'type': 'save_settings_response',
                            'request_id': parsed_data.get('request_id'),
                            'success': success,
                            'error': None if success else 'Failed to save settings'
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        continue
                    elif message_type == 'get_events':
                        # Return stored events
                        events = settings_manager.get_events()
                        response = {
                            'type': 'events_response',
                            'request_id': parsed_data.get('request_id'),
                            'payload': {'events': events}
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        continue
                    elif message_type == 'save_event':
                        # Save a new event
                        event_data = parsed_data.get('payload', {})
                        success = settings_manager.save_event(event_data)
                        if success:
                            response = {
                                'type': 'save_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': True,
                                'payload': event_data
                            }
                        else:
                            response = {
                                'type': 'save_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': False,
                                'error': 'Failed to save event'
                            }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        continue
                    elif message_type == 'update_event':
                        # Update an existing event
                        event_data = parsed_data.get('payload', {})
                        success = settings_manager.update_event(event_data)
                        if success:
                            response = {
                                'type': 'update_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': True,
                                'payload': event_data
                            }
                        else:
                            response = {
                                'type': 'update_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': False,
                                'error': 'Failed to update event'
                            }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        continue
                    elif message_type == 'delete_event':
                        # Delete an existing event
                        event_id = parsed_data.get('payload', {}).get('id')
                        if event_id:
                            success = settings_manager.delete_event(event_id)
                            response = {
                                'type': 'delete_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': success,
                                'error': None if success else 'Failed to delete event'
                            }
                        else:
                            response = {
                                'type': 'delete_event_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': False,
                                'error': 'Event ID is required'
                            }
                        await manager.send_personal_message(json.dumps(response), websocket)
                    elif message_type == 'face_recognition':
                        # Handle face recognition requests
                        action = parsed_data.get('action')
                        if action == 'get_models':
                            # Return all face recognition models
                            models = settings_manager.get_face_recognition_models()
                            response = {
                                'type': 'face_recognition_models_response',
                                'request_id': parsed_data.get('request_id'),
                                'payload': {'models': models}
                            }
                            await manager.send_personal_message(json.dumps(response), websocket)
                        elif action == 'save_model':
                            # Save a new face recognition model
                            model_data = parsed_data.get('payload', {})
                            
                            # Receive image data
                            image_data = await websocket.receive_bytes()
                            
                            # Save the image file
                            import uuid
                            import os
                            
                            
                            # Create faces directory if it doesn't exist
                            faces_dir = "./faces"
                            os.makedirs(faces_dir, exist_ok=True)
                            
                            # Generate unique filename
                            file_extension = model_data.get('extension', '.jpg')
                            filename = f"{uuid.uuid4()}{file_extension}"
                            file_path = os.path.join(faces_dir, filename)
                            
                            # Save the image file
                            with open(file_path, 'wb') as f:
                                f.write(image_data)
                            
                            # Update model data with file information
                            model_data.update({
                                'id': str(uuid.uuid4()),
                                'filename': filename,
                                'filepath': file_path,
                                'uploaded_at': datetime.now().isoformat(),
                                'isActive': True
                            })
                            
                            success = settings_manager.save_face_recognition_model(model_data)
                            response = {
                                'type': 'face_recognition_save_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': success,
                                'error': None if success else 'Failed to save face recognition model'
                            }
                            await manager.send_personal_message(json.dumps(response), websocket)
                        elif action == 'delete_model':
                            # Delete a face recognition model
                            model_id = parsed_data.get('payload', {}).get('id')
                            if model_id:
                                success = settings_manager.delete_face_recognition_model(model_id)
                                response = {
                                    'type': 'face_recognition_delete_response',
                                    'request_id': parsed_data.get('request_id'),
                                    'success': success,
                                    'error': None if success else 'Failed to delete face recognition model'
                                }
                            else:
                                response = {
                                    'type': 'face_recognition_delete_response',
                                    'request_id': parsed_data.get('request_id'),
                                    'success': False,
                                    'error': 'Model ID is required'
                                }
                            await manager.send_personal_message(json.dumps(response), websocket)
            except json.JSONDecodeError:
                # Not a JSON message, continue with normal processing
                pass
            
            # Handle normal message - echo back as JSON for structured response
            try:
                from datetime import datetime as dt
                response = {
                    "type": "echo",
                    "message": data,
                    "timestamp": str(dt.now())
                }
                await manager.send_personal_message(json.dumps(response), websocket)
            except Exception as e:
                print(f"Error sending echo response: {e}")
    except WebSocketDisconnect:
        # Remove disconnected socket from active list if present
        manager.disconnect(websocket)
        # Safely notify remaining connected clients that one has disconnected
        for conn in list(manager.active_connections):
            try:
                await manager.send_personal_message(json.dumps({
                    "type": "notification",
                    "message": "Client disconnected",
                    "timestamp": str(dt.now())
                }), conn)
            except Exception:
                # ignore errors when sending to other clients
                pass

@app.websocket("/info")
async def send_info(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            # Network percent over the interval between iterations
            net_io = psutil.net_io_counters()
            up_time = time.time() - psutil.boot_time()
            curr_bytes = net_io.bytes_sent + net_io.bytes_recv
            now = time.time()
            prev_bytes = getattr(send_info, "_prev_net_bytes", None)
            prev_time = getattr(send_info, "_prev_net_time", None)
            if prev_bytes is None or prev_time is None:
                net = 0.0
            else:
                delta_bytes = curr_bytes - prev_bytes
                delta_t = max(now - prev_time, 1e-6)
                bps = (delta_bytes * 8) / delta_t  # bits per second
                total_mbps = sum(s.speed for s in psutil.net_if_stats().values() if s.isup and s.speed)
                if total_mbps:
                    total_bps = total_mbps * 1_000_000
                    net = min(100.0, (bps / total_bps) * 100)
                else:
                    net = 0.0
            send_info._prev_net_bytes = curr_bytes
            send_info._prev_net_time = now

            # GPU utilization percent (use first device if available)
            deviceCount = pynvml.nvmlDeviceGetCount()
            if deviceCount > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu = float(util.gpu)
            else:
                gpu = 0.0
            import json 
            await manager.send_personal_message(json.dumps({"CPU": cpu, "Memory": memory, "Network": net, "GPU": gpu,"UP_TIME":up_time}), websocket)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def create_decoder():
    config = pocketsphinx.Decoder.default_config()
    config.set_string("-hmm", pathjoin(MODEL_PATH, "en-us", "en-us"))
    config.set_string("-dict", pathjoin(MODEL_PATH, "en-us", "cmudict-en-us.dict"))
    config.set_float("-kws_threshold", 1e-40)
    config.set_boolean("-logfn", False)
    
    decoder = pocketsphinx.Decoder(config)
    # Configure keyphrase search after decoder creation
    try:
        decoder.set_keyphrase('wakeup', 'jarvis')
        decoder.set_search('wakeup')
        print("Decoder configured with keyphrase search for 'jarvis'")
    except Exception as e:
        print(f"Failed to set keyphrase: {e}")
    
    return decoder

@app.websocket("/face_recognition")
async def face_recognition_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("Face Recognition WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, dict):
                    action = parsed_data.get('action')
                    print(f"Face recognition action: {action}")
                    
                    if action == 'get_models':
                        # Get all face recognition models
                        models = settings_manager.get_face_recognition_models()
                        response = {
                            'type': 'face_recognition_models_response',
                            'request_id': parsed_data.get('request_id'),
                            'payload': {
                                'models': models
                            }
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        
                    elif action == 'save_model':
                        # Save a new face recognition model
                        model_data = parsed_data.get('payload', {})
                        
                        # Receive image data
                        image_data = await websocket.receive_bytes()
                        
                        # Save the image file
                        import uuid
                        import os
                        from datetime import datetime
                        
                        
                        # Generate unique filename
                        file_extension = model_data.get('extension', '.jpg')
                        filename = f"{uuid.uuid4()}{file_extension}"
                        file_path = os.path.join(faces_dir, filename)
                        
                        # Save the image file
                        with open(file_path, 'wb') as f:
                            f.write(image_data)
                        
                        # Update model data with file information
                        model_data.update({
                            'id': str(uuid.uuid4()),
                            'filename': filename,
                            'filepath': file_path,
                            'uploaded_at': datetime.now().isoformat(),
                            'isActive': True
                        })
                        
                        success = settings_manager.save_face_recognition_model(model_data)
                        response = {
                            'type': 'face_recognition_save_response',
                            'request_id': parsed_data.get('request_id'),
                            'success': success,
                            'error': None if success else 'Failed to save face recognition model'
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        
                    elif action == 'delete_model':
                        # Delete a face recognition model
                        model_id = parsed_data.get('payload', {}).get('id')
                        if model_id:
                            success = settings_manager.delete_face_recognition_model(model_id)
                            response = {
                                'type': 'face_recognition_delete_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': success,
                                'error': None if success else 'Failed to delete face recognition model'
                            }
                        else:
                            response = {
                                'type': 'face_recognition_delete_response',
                                'request_id': parsed_data.get('request_id'),
                                'success': False,
                                'error': 'Model ID is required'
                            }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        
                    else:
                        # Unknown action
                        response = {
                            'type': 'face_recognition_error',
                            'request_id': parsed_data.get('request_id'),
                            'error': f'Unknown action: {action}'
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                        
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                response = {
                    'type': 'face_recognition_error',
                    'error': 'Invalid JSON format'
                }
                await manager.send_personal_message(json.dumps(response), websocket)
                
    except WebSocketDisconnect:
        print("Face Recognition WebSocket disconnected")
    except Exception as e:
        print(f"Face Recognition WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@app.websocket("/hotword")
async def hotword(websocket: WebSocket):
    await manager.connect(websocket)
    print("Hotword WebSocket connected")
    
    decoder = create_decoder()
    decoder.start_utt()
    import json
    import wave
    from io import BytesIO
    
    try:
        while True:
            data = await websocket.receive_bytes()
            print(f"Received {len(data)} bytes")
            
            try:
                # Parse WAV file from received bytes
                wav_file = BytesIO(data)
                with wave.open(wav_file, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                
                # Process audio
                decoder.process_raw(frames, False, False)
                
                hyp = decoder.hyp()
                if hyp and hyp.hypstr:
                    best_score = hyp.best_score 
                    hyp_str = hyp.hypstr.lower()
                    print(f"Decoder hypothesis score: {best_score}")
                    print(f"Decoder hypothesis: {hyp_str}")
                    if 'jarvis' in hyp_str and best_score > 1e-40:
                        print("Wake word 'jarvis' detected!")
                        try:
                            await manager.send_personal_message(
                                json.dumps({"event": "wakeword_detected", "word": hyp_str}), 
                                websocket
                            )
                        except WebSocketDisconnect:
                            break
                        
                        # Reset decoder for next detection
                        decoder.end_utt()
                        decoder.start_utt()
                
            except Exception as e:
                print(f"Error processing audio: {e}")
                import traceback
                traceback.print_exc()
    
    except WebSocketDisconnect:
        print("Hotword WebSocket disconnected")
        manager.disconnect(websocket)
    finally:
        try:
            decoder.end_utt()
        except:
            pass
@app.websocket("/face-verification")
async def face_verification(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            from io import BytesIO
            dfs = df.find(BytesIO(data), db_path="")
            print(dfs)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)