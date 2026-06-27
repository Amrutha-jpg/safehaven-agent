import os
import base64
import hashlib
from cryptography.fernet import Fernet
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SecureDocumentServer")

# Resolve the workspace root as the grandparent of this file's location
WORKSPACE_ROOT = os.path.abspath(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
)

def get_fernet_cipher(raw_key: str) -> Fernet:
    """AES-256 Fernet key pipeline: derives or decodes a valid Fernet key."""
    try:
        decoded = base64.urlsafe_b64decode(raw_key.encode())
        if len(decoded) == 32:
            return Fernet(raw_key.encode())
    except Exception:
        pass

    # Correct Fernet Key Derivation:
    # Hash raw passphrase to 32 bytes and base64.urlsafe_b64encode it
    hashed = hashlib.sha256(raw_key.encode()).digest()
    derived_key = base64.urlsafe_b64encode(hashed)
    return Fernet(derived_key)

@mcp.tool()
def decrypt_file(file_path: str, key: str = None) -> str:
    """Decrypts a local workspace file using the secure Fernet key pipeline.

    Args:
        file_path: The absolute or relative path of the file to decrypt.
        key: The decryption key. Falls back to env if empty or missing.
    """
    try:
        # Normalize the requested path and the workspace root
        workspace_root = os.path.abspath(os.path.normpath(WORKSPACE_ROOT))
        normalized_path = os.path.abspath(os.path.normpath(file_path))

        # Enforce boundary check to prevent traversing outside workspace
        try:
            common = os.path.commonpath([workspace_root, normalized_path])
        except ValueError:
            return "Error: Access denied. File path resides on a different drive or is invalid."

        if common != workspace_root:
            return "Error: Access denied. File path traverses outside the execution workspace boundary."

        # Double-check for explicit backtracking sequences in the original or normalized path
        if ".." in file_path or ".." in normalized_path:
            return "Error: Backtracking directories ('..') are not permitted."

        if not os.path.exists(normalized_path):
            return f"Error: File not found at {file_path}."

        # Dynamic Environment Fallbacks
        decryption_key = key
        if not decryption_key:
            decryption_key = (
                os.environ.get("FERNET_KEY")
                or os.environ.get("DECRYPTION_KEY")
                or os.environ.get("SECURE_KEY")
            )

        if not decryption_key:
            return "Error: Decryption key is required."

        try:
            cipher = get_fernet_cipher(decryption_key)
        except Exception as e:
            return f"Error: Failed to initialize Fernet cipher: {str(e)}"

        with open(normalized_path, "rb") as f:
            encrypted_data = f.read()

        try:
            decrypted_bytes = cipher.decrypt(encrypted_data)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            return f"Error: Failed to decrypt file. Invalid key or corrupted data: {str(e)}"

    except Exception as e:
        return f"Error reading/decrypting file: {str(e)}"

if __name__ == "__main__":
    mcp.run()
