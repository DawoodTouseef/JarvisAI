import warnings
import logging
import os
# Suppress websockets and other library deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")

# Configure centralized logging
# Use environment variable to control log level (default: INFO for production)
log_level = os.getenv('JARVIS_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.connection_manager import ConnectionManager
import psutil
import asyncio
import pynvml
import time
import pocketsphinx
from os.path import join as pathjoin
from server.settings import settings_manager
import json
from datetime import datetime
from deepface import DeepFace as df  
from pathlib import Path
from server.config import jarvis_cache

from server.database.database import engine, Base
from server.database.models import *  # Import models so they register with Base
from server.services.reminder_service import get_reminder_agent


JARVIS_DIR = Path(__file__).resolve().parent

# Create faces directory if it doesn't exist
faces_dir = os.path.join( jarvis_cache, "faces" )

logger.info("Creating faces directory if it doesn't exist... %s", faces_dir)
os.makedirs(faces_dir,exist_ok=True)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up JARVIS backend...")
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    reminder_agent = get_reminder_agent()
    await reminder_agent.start()
    app.state.reminder_agent = reminder_agent
    yield
    # Shutdown logic
    logger.info("Shutting down JARVIS backend...")
    try:
        reminder_agent = getattr(app.state, "reminder_agent", None)
        if reminder_agent:
            await reminder_agent.stop()
        settings_manager.close()
        # Also close the task manager's database
    except Exception as e:
        logger.error("Error during shutdown: %s", e)

app = FastAPI(
    title="Jarvis websocket server",
    lifespan=lifespan,
    docs_url="/docs",
)


manager = ConnectionManager()

# Initialize agent integration

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
                    logger.debug("Received message type: %s", message_type)
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
                            faces_dir = "faces"
                            os.makedirs(faces_dir, exist_ok=True)
                            
                            # Generate unique filename
                            file_extension = model_data.get('extension', '.jpg')
                            filename = f"{uuid.uuid4()}{file_extension}"
                            file_path = os.path.join(jarvis_cache,faces_dir, filename)
                            
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
                logger.error("Error sending echo response: %s", e)
    except (WebSocketDisconnect, RuntimeError):
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
    except (WebSocketDisconnect, RuntimeError):
        manager.disconnect(websocket)


def create_decoder():
    # Using modern PocketSphinx 5.0.4 API for cleaner initialization
    decoder = pocketsphinx.Decoder(
        hmm=pathjoin(MODEL_PATH, "en-us", "en-us"),
        dict=pathjoin(MODEL_PATH, "en-us", "cmudict-en-us.dict"),
        keyphrase="jarvis",
        kws_threshold=1e-20,
        logfn=os.devnull
    )
    return decoder

@app.websocket("/face_recognition")
async def face_recognition_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("Face Recognition WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, dict):
                    action = parsed_data.get('action')
                    logger.debug("Face recognition action: %s", action)
                    
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
                        file_path = os.path.join(jarvis_cache,faces_dir, filename)
                        
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
                logger.error("JSON decode error: %s", e)
                response = {
                    'type': 'face_recognition_error',
                    'error': 'Invalid JSON format'
                }
                await manager.send_personal_message(json.dumps(response), websocket)
                
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Face Recognition WebSocket disconnected")
    except Exception as e:
        logger.error("Face Recognition WebSocket error: %s", e)
    finally:
        manager.disconnect(websocket)


@app.websocket("/hotword")
async def hotword(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("Hotword WebSocket connected")
    
    decoder = create_decoder()
    decoder.start_utt()
    import json
    
    try:
        while True:
            data = await websocket.receive_bytes()
            logger.debug("Received %d bytes", len(data))
            
            try:
                # The frontend sends raw PCM bytes (Int16, 16kHz, Mono)
                # No longer using wave.open as it requires a RIFF header
                decoder.process_raw(data, False, False)
                
                hyp = decoder.hyp()
                if hyp and hyp.hypstr:
                    best_score = hyp.best_score 
                    hyp_str = hyp.hypstr.lower()
                    logger.debug("Decoder hypothesis score: %s", best_score)
                    logger.debug("Decoder hypothesis: %s", hyp_str)
                    if 'jarvis' in hyp_str and best_score > 1e-40:
                        logger.info("Wake word 'jarvis' detected!")
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
                logger.exception("Error processing audio: %s", e)
    
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Hotword WebSocket disconnected")
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
            dfs = df.find(BytesIO(data), db_path=faces_dir)
            logger.debug("Face verification result: %s", dfs)
            
    except (WebSocketDisconnect, RuntimeError):
        manager.disconnect(websocket)

@app.websocket("/voice-assistant")
async def voice_assistant_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice assistant.
    
    Uses OrchestratorSession for strict protocol compliance.
    One orchestrator instance per connection.
    """
    from server.orchestrator_session import OrchestratorSession
    
    await manager.connect(websocket)
    logger.info("Voice Assistant WebSocket connected")
    
    # Create send callback for this WebSocket
    async def send_to_websocket(message: dict):
        """Send message to WebSocket as JSON."""
        try:
            await manager.send_personal_message(json.dumps(message), websocket)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
    
    # Create orchestrator session for this connection
    session = OrchestratorSession(
        session_id=f"ws_{id(websocket)}",
        websocket_send_callback=send_to_websocket
    )

    reminder_agent = getattr(app.state, "reminder_agent", None)
    reminder_callback = None
    if reminder_agent:
        async def reminder_callback(event_type: str, task_id: str, payload: dict):
            await session.handle_external_event(event_type, task_id, payload)

        reminder_agent.add_event_callback(reminder_callback)
        async def submit_autonomous_query(text: str, meta: dict):
            return await session.submit_autonomous_query(text)

        reminder_agent.set_submit_query_callback(submit_autonomous_query)
    
    try:
        while True:
            # Receive text message
            data = await websocket.receive_text()
            
            try:
                parsed_data = json.loads(data)
                message_type = parsed_data.get("type")
                payload = parsed_data.get("payload", {})
                
                logger.debug(f"Voice Assistant received: {message_type}")
                
                # Route messages according to strict protocol
                if message_type == "user_query":
                    # Handle user query
                    text = payload.get("text")
                    auth_token = payload.get("auth_token") or os.getenv("OPENAI_API_KEY")
                    base_url = payload.get("base_url") or os.getenv("OPENAI_API_BASE")
                    
                    if text:
                        task_id = await session.handle_user_query(
                            text=text,
                            auth_token=auth_token,
                            base_url=base_url,
                            request_id=parsed_data.get("request_id")
                        )
                        
                        # Send acknowledgement
                        await send_to_websocket({
                            "type": "user_query_ack",
                            "task_id": task_id,
                            "request_id": parsed_data.get("request_id"),
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        send_to_websocket({
                            "type": "assistant_text_final",
                            "task_id": task_id,
                            "request_id": parsed_data.get("request_id"),
                            "timestamp": datetime.now().isoformat()
                        })
                
                elif message_type == "clarification_response":
                    # Handle clarification response
                    task_id = payload.get("task_id")
                    response_text = payload.get("text")
                    
                    if task_id and response_text:
                        await session.handle_clarification_response(task_id, response_text)
                    else:
                        raise ValueError("task_id and text are required")
                
                elif message_type == "permission_response":
                    # Handle permission response
                    task_id = payload.get("task_id")
                    approved = payload.get("approved", False)
                    
                    if task_id is not None:
                        await session.handle_permission_response(task_id, approved)
                    else:
                        raise ValueError("task_id is required")
                
                elif message_type == "vision_input":
                    # Handle incoming vision input (image bytes follow JSON)
                    metadata = payload or {}
                    image_bytes = await websocket.receive_bytes()
                    stored = await session.store_vision_input(image_bytes, metadata)
                    await send_to_websocket({
                        "type": "vision_input_ack",
                        "task_id": session.active_task_id,
                        "payload": {"stored": stored},
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "screen_context":
                    # Store screen text/context without an image
                    text = payload.get("text", "")
                    meta = payload.get("metadata", {})
                    from server.services.context.context_store import ContextStore
                    stored = ContextStore.set_screen_text(session.session_id, text, meta)
                    await send_to_websocket({
                        "type": "screen_context_ack",
                        "task_id": session.active_task_id,
                        "payload": {"stored": stored},
                        "timestamp": datetime.now().isoformat()
                    })

                elif message_type == "autonomous_permission_response":
                    # Handle autonomous permission response
                    request_id = payload.get("request_id")
                    approved = payload.get("approved", False)
                    if request_id and reminder_agent:
                        reminder_agent.resolve_permission(request_id, approved)
                    else:
                        raise ValueError("request_id is required")
                
                elif message_type == "interrupt":
                    # Handle interrupt
                    task_id = parsed_data.get("task_id")
                    if task_id:
                        await session.handle_interrupt(task_id)
                
                elif message_type == "cancel_task":
                    # Handle task cancellation
                    task_id = payload.get("task_id")
                    if task_id:
                        await session.handle_cancel_task(task_id)
                
                else:
                    # Unknown message type
                    logger.warning(f"Unknown message type: {message_type}")
                    await send_to_websocket({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            except json.JSONDecodeError:
                await send_to_websocket({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.exception(f"Error processing voice assistant message: {e}")
                await send_to_websocket({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Voice Assistant WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice Assistant WebSocket error: {e}")
    finally:
        # Clean up session
        if reminder_agent and reminder_callback:
            reminder_agent.remove_event_callback(reminder_callback)
            reminder_agent.clear_submit_query_callback()
        await session.disconnect()
        manager.disconnect(websocket)
        logger.info("Voice Assistant session cleaned up")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
