import blowfish
import base64

from datetime import datetime, timezone
from time import gmtime, strftime

def convert_datetime_to_timestamp(date_and_time):
    attr = date_and_time.split('-')
    dt = datetime(year=int(attr[0]), month=int(attr[1]), 
                  day=int(attr[2]), hour=int(attr[3]), minute=int(attr[4]))
    timestamp = dt.replace(tzinfo=timezone.utc).timestamp()
    return timestamp

def crypt_password(password, salt):
    key_bytes = salt.encode('utf-8')
    cipher = blowfish.Cipher(key_bytes)
    msg_bytes = password.encode('utf-8')
        
    block_size = 8
    padding_len = -len(msg_bytes) % block_size
    msg_bytes = msg_bytes.ljust(len(msg_bytes) + padding_len, b'\0')
        
    data_encrypted = b"".join(cipher.encrypt_ecb(msg_bytes))
    crypted_bytes = base64.b64encode(data_encrypted)
    crypted_base64 = crypted_bytes.decode('utf-8')
    return crypted_base64

def simplify_json_array(json_array):
    result = []
    for item in json_array:
        result.append(item['DISPLAY_NAME'])
    return result

def get_int_representation_of_violation_level(violation_level):
    if violation_level == 'High':
        return 3
    elif violation_level == 'Medium':
        return 2
    elif violation_level == 'Low':
        return 1
    else:
        return 0