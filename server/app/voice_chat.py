"""v0.193: Voice-to-Chat Bridge."""
import asyncio
import json
import io
import logging
from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types
from pydub import AudioSegment
import edge_tts

from .agent.santosh import run as run_chat
from .config import get_settings
from .events import bus

log = logging.getLogger("santosh.voice_chat")

async def tts_pcm(text: str) -> bytes:
    """Generate speech and convert to raw PCM (24kHz, 16-bit, mono) for Flutter."""
    if not text.strip():
        return b""
    # Use Indian English voice
    communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural")
    mp3_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_data += chunk["data"]
    if not mp3_data:
        return b""
    audio = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
    audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2)
    return audio.raw_data

async def voice_chat_endpoint(websocket: WebSocket, tenant_id: str, conversation_id: str):
    await websocket.accept()
    log.info(f"Voice-Chat connected for {tenant_id}")
    
    client = genai.Client(api_key=get_settings().gemini_api_key)
    stt_buffer = ""
    
    async def flush_stt():
        nonlocal stt_buffer
        if not stt_buffer.strip():
            return
        text = stt_buffer.strip()
        stt_buffer = ""
        # Run the Chat Agent (Opus 5.5) in the background
        asyncio.create_task(run_chat(tenant_id, conversation_id, text, actor="voice"))

    try:
        # We only need TEXT out from Gemini Live, since the actual brain is our Chat Agent
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            input_audio_transcription={},
        )
        
        # Use the same model as your existing voice.py
        model_name = get_settings().gemini_live_model or "gemini-2.0-flash-exp"
        
        async with client.aio.live.connect(model=model_name, config=config) as session:
            
            async def _send_audio():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            # Send phone mic audio to Gemini Live for STT
                            await session.send_realtime_input(
                                audio=types.Blob(data=data["bytes"], mime_type="audio/pcm;rate=16000")
                            )
                        elif "text" in data:
                            msg = json.loads(data["text"])
                            if msg.get("type") == "user_text":
                                asyncio.create_task(run_chat(tenant_id, conversation_id, msg["text"], actor="voice"))
                except WebSocketDisconnect:
                    pass

            async def _recv_stt():
                nonlocal stt_buffer
                try:
                    async for response in session.receive():
                        if response.server_content and response.server_content.input_transcription:
                            text = response.server_content.input_transcription.text
                            if text:
                                stt_buffer += text
                                # Send STT to client for UI display
                                await websocket.send_json({"type": "user_text", "text": text})
                                # Debounce: if no new text for 1.5 seconds, trigger the chat agent
                                if hasattr(_recv_stt, "timer"):
                                    _recv_stt.timer.cancel()
                                _recv_stt.timer = asyncio.create_task(_delay_flush())
                except Exception as e:
                    log.error(f"STT recv error: {e}")

            async def _delay_flush():
                await asyncio.sleep(1.5)
                await flush_stt()

            async def _listen_bus():
                try:
                    async for event in bus.subscribe(conversation_id):
                        if event.get("type") == "message":
                            txt = event.get("text", "")
                            await websocket.send_json({"type": "santosh_text", "text": txt})
                            # Speak the text
                            pcm = await tts_pcm(txt)
                            if pcm:
                                # Stream in 100ms chunks (4800 bytes at 24kHz)
                                for i in range(0, len(pcm), 4800):
                                    await websocket.send_bytes(pcm[i:i+4800])
                        elif event.get("type") == "step":
                            await websocket.send_json({"type": "tool", "label": event.get("label"), "state": event.get("state")})
                        elif event.get("type") == "todos":
                            await websocket.send_json({"type": "todos", "todos": event.get("todos")})
                except Exception as e:
                    log.error(f"Bus listen error: {e}")

            await asyncio.gather(
                asyncio.create_task(_send_audio()),
                asyncio.create_task(_recv_stt()),
                asyncio.create_task(_listen_bus())
            )
            
    except WebSocketDisconnect:
        log.info("Voice-Chat disconnected")
    except Exception as e:
        log.error(f"Voice-Chat error: {e}")
