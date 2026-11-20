import os
import sys
import random
from PIL import Image, ImageEnhance, ImageFilter
import subprocess

SRC_DIR = "/home/safin313/.gemini/antigravity/brain/07f4f4ec-90ad-4054-8ae3-714ad44d4da2"
DEST_DIR = "/home/safin313/Downloads/transify-main/src/frontend/static/photos"
os.makedirs(DEST_DIR, exist_ok=True)

SLOTS = {
    "welcome-sign": {
        "src": os.path.join(SRC_DIR, "welcome_sign_1795155770763.jpg"),
        "alt_names": ["hero-sign-welcome"],
        "crop": None,
        "desc": "Welcome hero sign communication"
    },
    "sign-camera": {
        "src": os.path.join(SRC_DIR, "slot2_sign_translator_png_1795155833466.jpg"),
        "alt_names": ["tile-sign-camera"],
        "crop": None,
        "desc": "Sign translator live camera placeholder"
    },
    "braille-page": {
        "src": os.path.join(SRC_DIR, "slot3_braille_scanner_1795155835486.jpg"),
        "alt_names": ["braille-bg-wide"],
        "crop": None,
        "desc": "Braille scanner document reading"
    },
    "voice-cafe": {
        "src": os.path.join(SRC_DIR, "slot_4_voice_hub_1795155832707.jpg"),
        "alt_names": ["voice-bg-wide"],
        "crop": None,
        "desc": "Voice hub speech-to-text in cafe"
    },
    "sign-bg-wide": {
        "src": os.path.join(SRC_DIR, "home_sign_tile_wide_1795155834939.jpg"),
        "alt_names": ["sign-wide"],
        "crop": None,
        "desc": "Wide view of woman signing toward laptop"
    },
    "tile-braille-embossed": {
        "src": os.path.join(SRC_DIR, "slot3_braille_scanner_1795155835486.jpg"),
        "alt_names": ["braille-tile"],
        "crop": "braille_fingertips",
        "desc": "Square crop of reading fingertips on Braille paper"
    },
    "tile-voice-caption": {
        "src": os.path.join(SRC_DIR, "slot_4_voice_hub_1795155832707.jpg"),
        "alt_names": ["voice-tile"],
        "crop": "voice_hands",
        "desc": "Square crop of phone and hands in cafe"
    },
    "auth-bg": {
        "src": os.path.join(SRC_DIR, "auth_screen_background_1795155895972.jpg"),
        "alt_names": ["login-hero-bg"],
        "crop": None,
        "desc": "Auth background blurred interior"
    },
    "empty-sign": {
        "src": os.path.join(SRC_DIR, "hand_sign_empty_state_1795155893481.jpg"),
        "alt_names": [],
        "crop": None,
        "desc": "Hand sign empty state"
    },
    "empty-braille": {
        "src": os.path.join(SRC_DIR, "braille_empty_state_1795155896293.jpg"),
        "alt_names": [],
        "crop": None,
        "desc": "Braille empty state"
    },
    "empty-voice": {
        "src": os.path.join(SRC_DIR, "voice_empty_state_1795155894616.jpg"),
        "alt_names": [],
        "crop": None,
        "desc": "Voice empty state"
    }
}

# Tone curve lookup table: lift shadows slightly by 8, gentle curve up to 255
LUT = [int(min(255, 8 + ((i / 255.0) ** 0.97) * (255 - 8))) for i in range(256)] * 3

def apply_grade(img):
    img = img.convert("RGB")
    
    # 1. Reduce saturation by 12%
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(0.88)
    
    # 2. Lift shadows via LUT
    img = img.point(LUT)
    
    return img

def do_crop(img, crop_type):
    w, h = img.size
    if crop_type == "braille_fingertips":
        side = min(w, h)
        left = int(w * 0.40)
        right = min(w, left + side)
        left = right - side
        top = 0
        bottom = side
        return img.crop((left, top, right, bottom))
    elif crop_type == "voice_hands":
        side = min(w, h)
        left = int(w * 0.25)
        right = min(w, left + side)
        left = max(0, right - side)
        top = int(h - side)
        bottom = h
        return img.crop((left, top, right, bottom))
    return img

def encode_avif(in_path, out_path):
    cmd = [
        "ffmpeg", "-y", "-i", in_path,
        "-c:v", "libsvtav1", "-crf", "35",
        "-pix_fmt", "yuv420p",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

print("Starting image processing pipeline...")

for name, info in SLOTS.items():
    src_path = info["src"]
    if not os.path.exists(src_path):
        print(f"Warning: {src_path} not found, skipping {name}")
        continue
    
    img = Image.open(src_path)
    if info["crop"]:
        img = do_crop(img, info["crop"])
    
    graded = apply_grade(img)
    all_names = [name] + info["alt_names"]
    
    # Save master images once
    base_target = name
    webp_path = os.path.join(DEST_DIR, f"{base_target}.webp")
    graded.save(webp_path, "WEBP", quality=75, method=6)
    
    jpg_path = os.path.join(DEST_DIR, f"{base_target}.jpg")
    graded.save(jpg_path, "JPEG", quality=82, progressive=True, optimize=True)
    
    # 24px LQIP blurred placeholder
    lqip_w = 24
    lqip_h = max(16, int(24 * (graded.height / graded.width)))
    lqip = graded.resize((lqip_w, lqip_h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(1.0))
    lqip_path = os.path.join(DEST_DIR, f"{base_target}_lqip.jpg")
    lqip.save(lqip_path, "JPEG", quality=40)
    
    # AVIF master via ffmpeg
    avif_path = os.path.join(DEST_DIR, f"{base_target}.avif")
    try:
        encode_avif(jpg_path, avif_path)
    except Exception as e:
        print(f"AVIF encoding failed for {base_target}: {e}")

    # Copy/link for aliases
    for alt_name in info["alt_names"]:
        for ext in [".webp", ".jpg", ".avif", "_lqip.jpg"]:
            src_f = os.path.join(DEST_DIR, f"{base_target}{ext}")
            dst_f = os.path.join(DEST_DIR, f"{alt_name}{ext}")
            if os.path.exists(src_f):
                import shutil
                shutil.copyfile(src_f, dst_f)

    # Multi-resolution versions: 1600px and 800px if width > target
    for width in [1600, 800]:
        if graded.width > width:
            target_h = int(graded.height * (width / graded.width))
            resized = graded.resize((width, target_h), Image.Resampling.LANCZOS)
            
            r_webp = os.path.join(DEST_DIR, f"{base_target}-{width}w.webp")
            resized.save(r_webp, "WEBP", quality=75)
            
            r_jpg = os.path.join(DEST_DIR, f"{base_target}-{width}w.jpg")
            resized.save(r_jpg, "JPEG", quality=82, progressive=True)
            
            r_avif = os.path.join(DEST_DIR, f"{base_target}-{width}w.avif")
            try:
                encode_avif(r_jpg, r_avif)
            except Exception:
                pass
            
            for alt_name in info["alt_names"]:
                for ext in [f"-{width}w.webp", f"-{width}w.jpg", f"-{width}w.avif"]:
                    src_f = os.path.join(DEST_DIR, f"{base_target}{ext}")
                    dst_f = os.path.join(DEST_DIR, f"{alt_name}{ext}")
                    if os.path.exists(src_f):
                        import shutil
                        shutil.copyfile(src_f, dst_f)

    print(f"Completed slot: {name} (aliases: {info['alt_names']})")

print("All slots processed successfully!")
