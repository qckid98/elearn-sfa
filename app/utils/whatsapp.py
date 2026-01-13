import requests
import os
import json

WA_API_URL = os.environ.get('WA_API_URL', 'http://wabot:3000')


def check_wa_status():
    """
    Check if WhatsApp bot is connected and active.
    Returns dict with status info.
    """
    try:
        response = requests.get(f"{WA_API_URL}/user/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Check if we have valid user data
            if data.get('results') and data['results'].get('verified_name'):
                return {
                    'connected': True,
                    'name': data['results'].get('verified_name') or data['results'].get('push_name', 'WhatsApp'),
                    'phone': data['results'].get('phone', '-'),
                    'status': 'active'
                }
            elif data.get('results'):
                return {
                    'connected': True,
                    'name': data['results'].get('push_name', 'WhatsApp'),
                    'phone': data['results'].get('phone', '-'),
                    'status': 'active'
                }
        return {'connected': False, 'status': 'disconnected', 'name': None, 'phone': None}
    except requests.exceptions.Timeout:
        return {'connected': False, 'status': 'timeout', 'name': None, 'phone': None}
    except Exception as e:
        return {'connected': False, 'status': 'error', 'error': str(e), 'name': None, 'phone': None}


def get_wa_qr():
    """
    Get QR code URL for WhatsApp login.
    Returns dict with qr_link if available.
    """
    try:
        response = requests.get(f"{WA_API_URL}/app/login", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and data['results'].get('qr_link'):
                return {
                    'success': True,
                    'qr_link': data['results']['qr_link'],
                    'duration': data['results'].get('qr_duration', 60)
                }
        return {'success': False, 'error': 'QR code not available'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout connecting to WA Bot'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


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