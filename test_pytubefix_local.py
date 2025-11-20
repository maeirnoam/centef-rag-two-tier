"""
Test pytubefix locally to see if YouTube blocks the download.
This helps determine if it's a Hostinger IP issue or a general pytubefix issue.
"""
from pytubefix import YouTube

print("=" * 70)
print("Testing pytubefix on Local Machine")
print("=" * 70)

# Test with the same video
test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
print(f"Testing URL: {test_url}")
print()

try:
    print("Creating YouTube object...")
    yt = YouTube(test_url)

    print(f"✓ Successfully connected to YouTube")
    print(f"  Title: {yt.title}")
    print(f"  Author: {yt.author}")
    print(f"  Length: {yt.length} seconds")
    print()

    print("Getting audio stream...")
    audio_stream = yt.streams.filter(only_audio=True).first()

    if audio_stream:
        print(f"✓ Audio stream found")
        print(f"  File size: {audio_stream.filesize / 1024 / 1024:.2f} MB")
        print(f"  MIME type: {audio_stream.mime_type}")
        print()

        download = input("Download audio to test folder? (y/n): ").strip().lower()

        if download == 'y':
            print("Downloading...")
            output_file = audio_stream.download(output_path=".", filename="test_audio")
            print(f"✓ Downloaded successfully to: {output_file}")
        if download == 'n':
            print("Skipped download")
    else:
        print("✗ No audio stream found")

except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("If you see 'bot detection' error, pytubefix itself is being blocked by YouTube")
    print("If it works here but not on Hostinger, then Hostinger IPs are blocked")

print()
print("=" * 70)
