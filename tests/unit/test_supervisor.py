import os
import unittest
from app.mcp_decryption_server import decrypt_file, WORKSPACE_ROOT, get_fernet_cipher

class TestMcpDecryptionServer(unittest.TestCase):

    def test_mcp_decryption_server_boundaries(self):
        # 1. Setup secure temp test file within your execution workspace path
        test_file = os.path.join(WORKSPACE_ROOT, "test_data.txt")
        
        # Encrypt mock content using the derivation engine pipeline
        cipher = get_fernet_cipher("SV_SAFE_2026")
        encrypted_data = cipher.encrypt(b"SV_SAFE_2026_CONTENT")

        with open(test_file, "wb") as f:
            f.write(encrypted_data)
            
        try:
            # Test Case A: Valid dynamic decryption execution path
            res = decrypt_file(test_file, "SV_SAFE_2026")
            self.assertEqual(res, "SV_SAFE_2026_CONTENT")
            
            # Test Case B: Failed cryptographic attempt under incorrect key context
            res = decrypt_file(test_file, "WRONG_KEY")
            self.assertIn("Error: Failed to decrypt file", res)
            
            # Test Case C: Traversal intercept validation
            outside_file = os.path.abspath(os.path.join(WORKSPACE_ROOT, "..", "outside.txt"))
            res_outside = decrypt_file(outside_file, "SV_SAFE_2026")
            self.assertIn("Error: Access denied", res_outside)

        finally:
            # Structural filesystem cleanup lifecycle safety
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()