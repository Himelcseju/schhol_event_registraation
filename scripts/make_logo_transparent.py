"""Make logo background transparent (cream/white -> alpha). Run once from project root."""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
logo_path = os.path.join(static_dir, "logo.png")
if not os.path.isfile(logo_path):
    print("Logo not found at", logo_path)
    sys.exit(1)

img = Image.open(logo_path).convert("RGBA")
pixels = img.load()
w, h = img.size

# Treat light/cream pixels as background; make them transparent
# Adjust threshold if needed (higher = more pixels become transparent)
threshold = 240  # RGB all above this -> transparent
for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if r >= threshold and g >= threshold and b >= threshold:
            pixels[x, y] = (r, g, b, 0)

img.save(logo_path)
print("Saved transparent logo to", logo_path)
