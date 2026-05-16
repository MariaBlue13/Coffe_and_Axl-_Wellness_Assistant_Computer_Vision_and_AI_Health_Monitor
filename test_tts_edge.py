import asyncio
import edge_tts
import os


async def test():
    # Voci romanesti disponibile
    voices = await edge_tts.list_voices()
    ro_voices = [v for v in voices if v["Locale"].startswith("ro")]

    print("Voci romanesti disponibile:")
    for v in ro_voices:
        print(f"  {v['ShortName']} — {v['Gender']}")


asyncio.run(test())