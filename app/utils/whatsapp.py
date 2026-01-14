import requests
import os
import json

WA_API_URL = os.environ.get('WA_API_URL', 'http://wabot:3000')


def check_wa_status():
    """
    Check if WhatsApp bot is connected and active.
    Uses /app/status endpoint which returns is_connected and is_logged_in.
    Returns dict with status info.
    """
    try:
        # Use /app/status endpoint for connection status
        response = requests.get(f"{WA_API_URL}/app/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {})
            
            is_connected = results.get('is_connected', False)
            is_logged_in = results.get('is_logged_in', False)
            device_id = results.get('device_id', '')
            
            # Bot is considered active if both connected and logged in
            if is_connected and is_logged_in:
                # Try to get additional user info if available
                name = 'WhatsApp Bot'
                phone = device_id if device_id else '-'
                
                # Optionally fetch more details from /app/devices
                try:
                    devices_resp = requests.get(f"{WA_API_URL}/app/devices", timeout=3)
                    if devices_resp.status_code == 200:
                        devices_data = devices_resp.json()
                        devices = devices_data.get('results', [])
                        if devices and len(devices) > 0:
                            first_device = devices[0]
                            if isinstance(first_device, dict):
                                name = first_device.get('PushName', name)
                                phone = first_device.get('Device', {}).get('User', phone)
                except:
                    pass  # Use defaults if devices fetch fails
                
                return {
                    'connected': True,
                    'name': name,
                    'phone': phone,
                    'status': 'active'
                }
        
        # Not connected or error
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