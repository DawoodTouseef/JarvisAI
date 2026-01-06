from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from connection_manager import ConnectionManager
import psutil
import asyncio
import pynvml
import time
import pocketsphinx
from os.path import join as pathjoin
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
            await manager.send_personal_message(f"Received:{data}",websocket)
    except WebSocketDisconnect:
        # Remove disconnected socket from active list if present
        try:
            manager.disconnect(websocket)
        except ValueError:
            pass
        # Safely notify remaining connected clients that one has disconnected
        for conn in list(manager.active_connections):
            try:
                await manager.send_personal_message("Client disconnected", conn)
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
    except WebSocketDisconnect as e:
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
                    hyp_str = hyp.hypstr.lower()
                    print(f"Decoder hypothesis: {hyp_str}")
                    
                    if 'jarvis' in hyp_str:
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
                from os import remove
                remove(wav_file)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)