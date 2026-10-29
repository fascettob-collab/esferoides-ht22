# Convierte los stacks .oif (Olympus FV1000) a volumenes 8 bits livianos para el visor web.
# Uso: python preparar_datos.py  (desde la carpeta web/scripts)
import gzip, json, os, struct
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(os.path.dirname(__file__), "..", "data")

# [id, carpeta .oif.files, planos (1-based, inclusive), um/px original, um entre planos, titulo,
#  recorte (x0, y0, ancho, alto) en px originales o None, reduccion]
# 40x: planos 1-24 porque la muestra se movio despues del plano 24 (igual que el modelo de Fiji).
# 10x: recorte alrededor del esferoide (el campo de 1024 px es casi todo fondo).
VOLUMENES = [
    ("40x", "transfectadas/1_01.oif.files", (1, 24), 0.19775, 1.0, "Esferoide transfectado 40x", None, 2),
    ("10x", "transfectadas/1.oif.files", (1, 26), 0.6204, 2.0, "Esferoide transfectado 10x", (320, 340, 448, 368), 1),
]
CANALES = [("dapi", 1, 0.998), ("gfp", 2, 0.999), ("wga", 3, 0.998)]  # canal Olympus y percentil alto


def leer_tif(ruta):
    with open(ruta, "rb") as f:
        b = f.read()
    e = "<" if b[:2] == b"II" else ">"
    ifd = struct.unpack(e + "I", b[4:8])[0]
    n = struct.unpack(e + "H", b[ifd:ifd + 2])[0]
    tags = {}
    for i in range(n):
        t, typ, cnt, val = struct.unpack(e + "HHII", b[ifd + 2 + 12 * i: ifd + 14 + 12 * i])
        if typ == 3 and cnt == 1:
            val = struct.unpack(e + "H", b[ifd + 10 + 12 * i: ifd + 12 + 12 * i])[0]
        tags[t] = (typ, cnt, val)
    w, h = tags[256][2], tags[257][2]
    assert tags.get(259, (0, 0, 1))[2] == 1, "TIFF comprimido"
    typ, cnt, val = tags[273]
    if cnt == 1:
        off = val
    else:
        fmt = "I" if typ == 4 else "H"
        off = struct.unpack(e + fmt, b[val:val + (4 if typ == 4 else 2)])[0]
    return np.frombuffer(b, dtype=e + "u2", count=w * h, offset=off).reshape(h, w).astype(np.float32)


os.makedirs(OUT, exist_ok=True)
info = {}
for vid, carpeta, (z0, z1), umpx, umz, titulo, recorte, r in VOLUMENES:
    d = os.path.join(BASE, carpeta)
    canales = {}
    for nombre, c, phi in CANALES:
        planos = []
        for z in range(z0, z1 + 1):
            im = leer_tif(os.path.join(d, "s_C%03dZ%03d.tif" % (c, z)))
            if recorte:
                x0, y0, w, h = recorte
                im = im[y0:y0 + h, x0:x0 + w]
            im = im.reshape(im.shape[0] // r, r, im.shape[1] // r, r).mean(axis=(1, 3))
            planos.append(im)
        vol = np.stack(planos)  # z, y, x
        muestra = vol[::3, ::4, ::4].ravel()
        lo, hi = np.quantile(muestra, 0.01), np.quantile(muestra, phi)
        v8 = np.clip((vol - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
        with gzip.open(os.path.join(OUT, "%s_%s.bin.gz" % (vid, nombre)), "wb", 9) as f:
            f.write(v8.tobytes())
        canales[nombre] = "%s_%s.bin.gz" % (vid, nombre)
        print(vid, nombre, v8.shape, "rango", lo, hi)
    zz, yy, xx = v8.shape
    info[vid] = {"titulo": titulo, "dims": [xx, yy, zz], "um_px": umpx * r, "um_z": umz,
                 "planos": [z0, z1], "canales": canales}
with open(os.path.join(OUT, "volumenes.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
print(json.dumps(info, indent=1))
