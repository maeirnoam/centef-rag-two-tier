"""
Simple HTTP server to serve the frontend files.
Run this from the centef-rag-two-tier/apps/frontend directory.
Supports PORT environment variable for Cloud Run deployment.
"""
import http.server
import socketserver
import os
from pathlib import Path

# Use PORT from environment (Cloud Run) or default to 3000 for local dev
PORT = int(os.getenv("PORT", "3000"))
DIRECTORY = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"✓ Frontend server running at: http://localhost:{PORT}")
        print(f"✓ Serving files from: {DIRECTORY}")
        print(f"\nOpen your browser to:")
        print(f"  • Login:    http://localhost:{PORT}/login.html")
        print(f"  • Chat:     http://localhost:{PORT}/chat.html")
        print(f"  • Manifest: http://localhost:{PORT}/manifest.html")
        print(f"\nPress Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✓ Server stopped")
