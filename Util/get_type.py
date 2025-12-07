from Util.audio_util import get_url_media, get_binary_media, get_transcription

AUDIO_TRANSCRIPTION_CACHE = {}


def get_cached_transcription(id_audio: str) -> str | None:
  
    return AUDIO_TRANSCRIPTION_CACHE.get(id_audio)


def cache_transcription(id_audio: str, texto: str) -> None:
    AUDIO_TRANSCRIPTION_CACHE[id_audio] = texto


def get_type(message):
    tipo = message.get("type", "unknown")
    contenido = ""

    if tipo == "text":
        contenido = message.get("text", {}).get("body", "")

    elif tipo == "interactive":
        interactive = message.get("interactive", {})
        t = interactive.get("type")
        if t == "button_reply":
            contenido = interactive["button_reply"].get("id", "")
        elif t == "list_reply":
            contenido = interactive["list_reply"].get("id", "")
        else:
            print("⚠️ Tipo interactivo no reconocido")

    elif tipo == "location":
        loc = message.get("location", {})
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat and lon:
            contenido = f"{lat},{lon}"

    elif tipo == "audio":
        try:
            id_audio = message.get("audio", {}).get("id", "")
            print(f"🎵 Procesando audio con ID: {id_audio}")
            if not id_audio:
                print("⚠️ No se encontró ID de audio en el mensaje")
                contenido = "No pude procesar el audio. Por favor, envía un mensaje de texto."
            else:
                cached_text = get_cached_transcription(id_audio)
                if cached_text is not None:
                    print(f"✅ Usando transcripción cacheada para audio {id_audio}")
                    contenido = cached_text
                else:
                    print(f"📥 Obteniendo URL del audio {id_audio}...")
                    url = get_url_media(id_audio)
                    print(f"📥 URL obtenida: {url[:50]}...")
                    
                    print(f"📥 Descargando audio binario...")
                    binary_audio = get_binary_media(url)
                    print(f"📥 Audio descargado: {len(binary_audio)} bytes")
                    
                    print(f"🔄 Iniciando transcripción...")
                    contenido = get_transcription(binary_audio)
                    
                    cache_transcription(id_audio, contenido)
                    print(f"✅ Transcripción guardada en cache para audio {id_audio}")
        except Exception as error:
            import traceback
            error_type = type(error).__name__
            error_msg = str(error)
            print(f"⚠️ Error al procesar audio: {error_type} → {error_msg}")
            print(f"📋 Stack trace completo:")
            traceback.print_exc()
            
            if "429" in error_msg or "Too Many Requests" in error_msg:
                contenido = "⚠️ Se excedió el límite de solicitudes. Por favor, espera unos momentos y envía un mensaje de texto en su lugar."
            else:
                contenido = "No pude procesar el audio. Por favor, envía un mensaje de texto."

    else:
        print(f"⚠️ Tipo de mensaje no manejado: {tipo}")

    return tipo, contenido
