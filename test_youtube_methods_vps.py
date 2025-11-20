"""
Test different YouTube download methods on Hostinger VPS
Run this ON THE VPS to test pytubefix, yt-dlp, and different configurations
"""
import subprocess
import sys

print("=" * 80)
print("YouTube Download Methods Test - Hostinger VPS")
print("=" * 80)
print()

# Test video
test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
print(f"Test URL: {test_url}")
print()

# Test 1: pytubefix (current method)
print("Test 1: pytubefix (default)")
print("-" * 80)
try:
    from pytubefix import YouTube

    yt = YouTube(test_url)
    print(f"✓ Title: {yt.title}")
    print(f"✓ Author: {yt.author}")

    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream:
        print(f"✓ Audio stream found: {audio_stream.mime_type}")
    else:
        print("✗ No audio stream")

except Exception as e:
    print(f"✗ Failed: {e}")

print()

# Test 2: pytubefix with custom user agent
print("Test 2: pytubefix with custom User-Agent")
print("-" * 80)
try:
    from pytubefix import YouTube

    # Try with a realistic browser user agent
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    yt = YouTube(test_url, use_oauth=False, allow_oauth_cache=False)
    # Note: pytubefix doesn't directly support custom headers in constructor
    # but we're testing it anyway

    print(f"✓ Title: {yt.title}")
    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream:
        print(f"✓ Audio stream found: {audio_stream.mime_type}")
    else:
        print("✗ No audio stream")

except Exception as e:
    print(f"✗ Failed: {e}")

print()

# Test 3: Check if yt-dlp is installed
print("Test 3: yt-dlp")
print("-" * 80)
try:
    result = subprocess.run(
        ['yt-dlp', '--version'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        print(f"✓ yt-dlp installed: version {result.stdout.strip()}")

        # Try downloading metadata only
        print("  Testing metadata retrieval...")
        result = subprocess.run(
            ['yt-dlp', '--dump-json', '--no-warnings', test_url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            print(f"  ✓ Title: {data.get('title', 'Unknown')}")
            print(f"  ✓ Duration: {data.get('duration', 0)} seconds")
            print(f"  ✓ Uploader: {data.get('uploader', 'Unknown')}")
        else:
            print(f"  ✗ Metadata fetch failed: {result.stderr}")
    else:
        print("✗ yt-dlp not working")

except FileNotFoundError:
    print("✗ yt-dlp not installed")
    print("  To install: pip install yt-dlp")
except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 4: yt-dlp with custom user agent
print("Test 4: yt-dlp with custom User-Agent")
print("-" * 80)
try:
    result = subprocess.run(
        [
            'yt-dlp',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--dump-json',
            '--no-warnings',
            test_url
        ],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        print(f"✓ Title: {data.get('title', 'Unknown')}")
        print(f"✓ Works with custom User-Agent!")
    else:
        print(f"✗ Failed: {result.stderr}")

except FileNotFoundError:
    print("✗ yt-dlp not installed")
except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 5: yt-dlp with IP source binding (if multiple IPs available)
print("Test 5: yt-dlp with Source IP Binding")
print("-" * 80)
try:
    # Check available network interfaces
    result = subprocess.run(
        ['ip', 'addr', 'show'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        print("Available network interfaces:")
        # Parse for IP addresses
        import re
        ips = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
        for ip in ips:
            if not ip.startswith('127.'):
                print(f"  - {ip}")

        # Try binding to first non-localhost IP
        non_local_ips = [ip for ip in ips if not ip.startswith('127.')]
        if non_local_ips:
            test_ip = non_local_ips[0]
            print(f"\nTesting with source IP: {test_ip}")

            result = subprocess.run(
                ['yt-dlp', '--source-address', test_ip, '--dump-json', '--no-warnings', test_url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                print(f"  ✓ Works with source IP binding!")
                print(f"  ✓ Title: {data.get('title', 'Unknown')}")
            else:
                print(f"  ✗ Failed with source IP: {result.stderr[:200]}")
        else:
            print("No non-localhost IPs found")
    else:
        print("✗ Cannot list network interfaces")

except FileNotFoundError:
    print("✗ yt-dlp or ip command not available")
except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 6: Check for Tor/proxy options
print("Test 6: Proxy/Tor Availability")
print("-" * 80)
try:
    # Check if Tor is running
    result = subprocess.run(
        ['systemctl', 'is-active', 'tor'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0 and result.stdout.strip() == 'active':
        print("✓ Tor service is running")
        print("  Can use: --proxy socks5://127.0.0.1:9050")

        # Test yt-dlp with Tor
        print("  Testing yt-dlp through Tor...")
        result = subprocess.run(
            ['yt-dlp', '--proxy', 'socks5://127.0.0.1:9050', '--dump-json', '--no-warnings', test_url],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            print(f"  ✓ Works through Tor!")
            print(f"  ✓ Title: {data.get('title', 'Unknown')}")
        else:
            print(f"  ✗ Failed through Tor: {result.stderr[:200]}")
    else:
        print("✗ Tor not running")
        print("  To install: sudo apt-get install tor")
        print("  To start: sudo systemctl start tor")

except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 7: Network info
print("Test 7: Network Configuration")
print("-" * 80)
try:
    # Check public IP
    result = subprocess.run(
        ['curl', '-s', 'https://api.ipify.org'],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0:
        print(f"Public IP: {result.stdout.strip()}")

    # Check if behind proxy
    import os
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

    if http_proxy or https_proxy:
        print(f"HTTP Proxy: {http_proxy or 'Not set'}")
        print(f"HTTPS Proxy: {https_proxy or 'Not set'}")
    else:
        print("No proxy configured")

except Exception as e:
    print(f"Error checking network: {e}")

print()
print("=" * 80)
print("Summary")
print("=" * 80)
print("If pytubefix fails but yt-dlp works:")
print("  → Switch the service to use yt-dlp instead")
print()
print("If both fail:")
print("  → Hostinger IP is blocked by YouTube")
print("  → May need cookies or residential proxy")
print()
print("If custom User-Agent helps:")
print("  → Can add User-Agent spoofing to the service")
print("=" * 80)
