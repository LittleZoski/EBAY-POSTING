"""
Test image filtering logic
"""

import sys
import codecs

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Example image URLs from your JSON
test_images = [
    # FILTER - Has AC_SL pattern
    "https://m.media-amazon.com/images/I/51j1zxyiUGL._AC_SL1000_.jpg",
    "https://m.media-amazon.com/images/I/81FoRz9V7JL._AC_SL1500_.jpg",

    # KEEP - Valid product images (no AC_SL)
    "https://m.media-amazon.com/images/I/412u4r3dt+L.jpg",
    "https://m.media-amazon.com/images/I/51WeVFgqRhL.jpg",
    "https://m.media-amazon.com/images/I/41fohJJLrsL.jpg",
    "https://m.media-amazon.com/images/I/51XyQ2G-xgL.jpg",

    # FILTER OUT - Functional UI elements
    "https://m.media-amazon.com/images/G/01/HomeCustomProduct/360_icon_73x73v2.png",
    "https://m.media-amazon.com/images/G/01/HomeCustomProduct/imageBlock-360-thumbnail-icon-small.png",
    "https://m.media-amazon.com/images/I/51ISC2dUdqL._AC_SL1050_.jpg",
    "https://m.media-amazon.com/images/I/61abc123._AC_SL1500_.jpg",

    # FILTER OUT - More patterns
    "https://m.media-amazon.com/images/G/01/x-locale/common/transparent-pixel.gif",
    "https://m.media-amazon.com/images/G/01/digital/video/PKdp-play-icon-overlay.png",
]

print("=" * 80)
print("Image Filter Test")
print("=" * 80)

images = []
for img_url in test_images:
    # Apply same filter logic - AGGRESSIVE AC_SL filtering
    if "_AC_SL" in img_url or "AC_SL" in img_url:
        print(f"❌ FILTERED (AC pattern): {img_url}")
        continue
    if "PKdp-play-icon-overlay" in img_url or "play-icon" in img_url:
        print(f"❌ FILTERED (play icon): {img_url}")
        continue
    if "360_icon" in img_url or "360-icon" in img_url or "imageBlock" in img_url:
        print(f"❌ FILTERED (360/imageBlock): {img_url}")
        continue
    if "transparent-pixel" in img_url or "transparent_pixel" in img_url:
        print(f"❌ FILTERED (transparent): {img_url}")
        continue
    if "icon" in img_url.lower() and ("small" in img_url.lower() or "thumbnail" in img_url.lower()):
        print(f"❌ FILTERED (small icon): {img_url}")
        continue

    print(f"✅ KEPT: {img_url}")
    images.append(img_url)

print("\n" + "=" * 80)
print(f"Results: {len(test_images)} total -> {len(images)} kept, {len(test_images) - len(images)} filtered")
print("=" * 80)
