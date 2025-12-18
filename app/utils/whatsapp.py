import requests
import os
import json

WA_API_URL = os.environ.get('WA_API_URL', 'http://wabot:3000')

def send_wa_message(target_number, message):
    """
    Kirim pesan WA via Aldinokemal Bot.
    target_number: 
      - Personal: '62812345678@s.whatsapp.net' (Perhatikan akhiran ini untuk user)
      - Group: '12345678@g.us'
    """
    # Endpoint untuk send message di repo aldinokemal biasanya /send/message
    # URL Path diperbaiki sesuai code Go: /send/message
    url = f"{WA_API_URL}/send/message" 
    
    # Payload
    payload = {
        "phone": target_number,
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"WA Sukses: {response.json()}")
            return True
        else:
            print(f"WA Gagal: {response.text}")
            return False
    except Exception as e:
        print(f"Error koneksi ke WA Bot: {e}")
        return False