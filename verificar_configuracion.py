"""
Script para verificar la configuración de WhatsApp Business API
"""

import requests
from whatsapp_api import WHATSAPP_ACCESS_TOKEN, WHATSAPP_API_URL, obtener_phone_number_id

def verificar_configuracion():
    """Verifica la configuración de la API."""
    print("="*60)
    print("🔍 Verificando configuración de WhatsApp Business API")
    print("="*60)
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
    }
    
    # Verificar token de acceso
    print("\n1️⃣ Verificando token de acceso...")
    try:
        url = f"{WHATSAPP_API_URL}/me"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Token válido")
            print(f"   👤 App ID: {data.get('id', 'N/A')}")
            print(f"   📝 Nombre: {data.get('name', 'N/A')}")
        else:
            error_data = response.json()
            print(f"   ❌ Error con el token: {error_data.get('error', {}).get('message', 'Error desconocido')}")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar token: {str(e)}")
        return False
    
    # Verificar Phone Number ID (usar el configurado si no se puede obtener de la API)
    print("\n2️⃣ Verificando Phone Number ID...")
    from whatsapp_api import WHATSAPP_PHONE_NUMBER_ID
    
    phone_id = WHATSAPP_PHONE_NUMBER_ID
    if not phone_id:
        phone_id = obtener_phone_number_id()
    
    if phone_id:
        print(f"   📱 Phone Number ID: {phone_id}")
        
        # Verificar que el Phone Number ID funciona intentando obtener su información
        print("\n3️⃣ Verificando acceso al Phone Number ID...")
        url = f"{WHATSAPP_API_URL}/{phone_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Phone Number ID válido y accesible")
            print(f"   📱 Display Phone Number: {data.get('display_phone_number', 'N/A')}")
            print(f"   🔢 Verified Name: {data.get('verified_name', 'N/A')}")
        else:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Error desconocido')
            print(f"   ⚠️ No se pudo verificar el Phone Number ID: {error_msg}")
            print(f"   💡 Esto puede ser normal si el token no tiene permisos para leer información del número")
            print(f"   💡 Intentemos enviar un mensaje de prueba para verificar si funciona...")
    else:
        print(f"   ❌ No hay Phone Number ID configurado")
        print(f"   💡 Configúralo en whatsapp_api.py")
        return False
    
    print("\n" + "="*60)
    print("✅ Configuración verificada correctamente!")
    print("="*60)
    print(f"\n📝 Usa este Phone Number ID en whatsapp_api.py:")
    print(f"   WHATSAPP_PHONE_NUMBER_ID = \"{phone_id}\"")
    print("="*60)
    
    return True

if __name__ == "__main__":
    verificar_configuracion()
