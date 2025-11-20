"""
Verify that the YouTube downloader is actually using Tor
"""
import requests

VPS_IP = "145.223.73.61"
API_KEY = "540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55"

print("=" * 70)
print("Verify Tor Usage in YouTube Downloader")
print("=" * 70)
print()

# Check the health endpoint to see Tor status
print("Checking health endpoint...")
response = requests.get(f"http://{VPS_IP}:8080/health")

if response.status_code == 200:
    health = response.json()
    print(f"Status: {health.get('status')}")
    print(f"yt-dlp: {health.get('ytdlp')}")
    print(f"Tor: {health.get('tor')}")
    print(f"ffmpeg: {health.get('ffmpeg')}")
    print()

    if health.get('tor') == 'running':
        print("✓ Tor is running on VPS")
    else:
        print("✗ Tor is NOT running - downloads will fail!")
        exit(1)
else:
    print(f"✗ Cannot reach health endpoint: {response.status_code}")
    exit(1)

print()
print("=" * 70)
print("To see Tor being used, check VPS logs:")
print("  ssh root@145.223.73.61")
print("  journalctl -u youtube-downloader -f")
print()
print("You should see:")
print("  'Starting download with yt-dlp (via Tor): ...'")
print("  '--proxy socks5://127.0.0.1:9050'")
print("=" * 70)
