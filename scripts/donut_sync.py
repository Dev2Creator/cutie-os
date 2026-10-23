import asyncio
import math
import struct
import sys
from bleak import BleakClient
from PIL import Image, ImageDraw, ImageFont

MAC = "B2:17:5A:9A:AB:E8"
WRITE_CHAR = "0000ae01-0000-1000-8000-00805f9b34fb"

# Resolution aur Frame Count
WIDTH, HEIGHT = 120, 120
FRAMES = 16

def render_donut_frames():
    print("⏳ [1/3] Calculating 3D ASCII Torus & Rendering Frames...")
    font = ImageFont.load_default()
    packed_stream = bytearray()

    for f_idx in range(FRAMES):
        A = f_idx * (2 * math.pi / FRAMES)
        B = f_idx * (math.pi / FRAMES)
        cosA, sinA = math.cos(A), math.sin(A)
        cosB, sinB = math.cos(B), math.sin(B)

        cols, rows = 32, 32
        b = [' '] * (cols * rows)
        z = [0.0] * (cols * rows)

        for j in [x * 0.1 for x in range(0, 62)]:
            cosj, sinj = math.cos(j), math.sin(j)
            for i in [x * 0.05 for x in range(0, 125)]:
                sini, cosi = math.sin(i), math.cos(i)
                h = cosj + 2
                D = 1 / (sini * h * sinA + sinj * cosA + 5)
                t = sini * h * cosA - sinj * sinA
                x = int(cols / 2 + 20 * D * (cosi * h * cosB - t * sinB) * 0.5)
                y = int(rows / 2 + 10 * D * (cosi * h * sinB + t * cosB))
                o = x + cols * y
                N = int(8 * ((sinj * sinA - sini * cosj * cosA) * cosB - sini * cosj * sinA - sinj * cosA - cosi * cosj * sinB))
                if 0 <= y < rows and 0 <= x < cols and D > z[o]:
                    z[o] = D
                    b[o] = ".,-~:;=!*#$@"[max(N, 0)]

        # Canvas generate karo
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        for r in range(rows):
            line = "".join(b[r * cols : (r + 1) * cols])
            draw.text((4, r * 3), line, fill=(57, 197, 187), font=font)

        # Frame ko RGB565 binary me convert karo
        for y in range(HEIGHT):
            for x in range(WIDTH):
                red, green, blue = img.getpixel((x, y))
                val = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
                packed_stream.extend(struct.pack("<H", val))

    print(f"✔ Done! Generated {FRAMES} frames ({len(packed_stream)} bytes)")
    return packed_stream

async def transmit_ble(payload):
    print(f"⏳ [2/3] Connecting to {MAC} via BLE...")
    try:
        async with BleakClient(MAC) as client:
            print("✔ Connected! Streaming packets to watch buffer...")
            chunk_size = 20  # Safe MTU packet limit
            total = len(payload)
            
            for i in range(0, total, chunk_size):
                chunk = payload[i:i + chunk_size]
                await client.write_gatt_char(WRITE_CHAR, chunk, response=False)
                await asyncio.sleep(0.008)
                
                # Progress indicator
                percent = (i / total) * 100
                sys.stdout.write(f"\rProgress: [{int(percent)}%] ({i}/{total} bytes)")
                sys.stdout.flush()

            print("\n✔ [3/3] Payload stream complete!")
    except Exception as e:
        print(f"\n❌ BLE Error: {e}")

if __name__ == "__main__":
    stream = render_donut_frames()
    asyncio.run(transmit_ble(stream))
