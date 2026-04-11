from cryptography.fernet import Fernet
import os

def decrypt_manifest():
    print("[*] Vanguard Logistics - Unauthorized Decryption Tool")
    
    # Check if the attacker found both files
    if not os.path.exists('vault.key') or not os.path.exists('manifest.enc'):
        print("[-] Error: Missing vault.key or manifest.enc.")
        return

    # Read the key
    with open('vault.key', 'rb') as key_file:
        key = key_file.read()

    # Initialize the cipher
    cipher_suite = Fernet(key)

    # Read the encrypted flag
    with open('manifest.enc', 'rb') as enc_file:
        cipher_text = enc_file.read()

    # Decrypt and reveal!
    try:
        plain_text = cipher_suite.decrypt(cipher_text)
        print("\n[+] DECRYPTION SUCCESSFUL!")
        print(f"[+] EXTRACTED FLAG: {plain_text.decode('utf-8')}\n")
    except Exception as e:
        print(f"[-] Decryption failed: {e}")

if __name__ == '__main__':
    decrypt_manifest()