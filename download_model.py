# download_model.py
import os
import requests

# Ruta local de caché de layoutparser
base_dir = os.path.expanduser("~/.cache/layoutparser/layout_models/PubLayNet/ppyolov2")
os.makedirs(base_dir, exist_ok=True)

# Enlaces oficiales de Dropbox
urls = {
    "config.yaml": "https://www.dropbox.com/scl/fi/d2xrcgrv7x2rr8p9ztpvm/config.yaml?rlkey=nckm1w92qcmu3gwt5fz4mu62k&dl=1",
    "model_final.pth": "https://www.dropbox.com/scl/fi/7fgvf6rwz64iw6o9sjnaw/model_final.pth?rlkey=4jqxvygfu7pajl3jjgbgqwq4g&dl=1"
}

# Descargar cada archivo
for name, url in urls.items():
    local_path = os.path.join(base_dir, name)
    if not os.path.exists(local_path):
        print(f"🔽 Descargando {name}...")
        r = requests.get(url)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        print(f"✅ Guardado en: {local_path}")
    else:
        print(f"🟢 Ya existe: {local_path}")

print("\n🎉 Modelo descargado y listo para usar.")