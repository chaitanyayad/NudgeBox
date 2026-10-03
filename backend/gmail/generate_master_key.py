import os
import base64

def main():
    key = os.urandom(32)
    b64_key = base64.b64encode(key).decode('utf-8')
    print("New 32-byte master key (base64):")
    print(b64_key)

if __name__ == "__main__":
    main()
