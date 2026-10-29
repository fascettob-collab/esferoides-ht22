# Convierte los stacks .oif (Olympus FV1000) a volumenes 8 bits livianos para el visor web.
# Uso: python preparar_datos.py  (desde la carpeta web/scripts)
import gzip, json, os, struct
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(os.path.dirname(__file__), "..", "data")

# [id, carpeta .oif.files, planos (1-based, inclusive), um/px original, um entre planos, titulo,
#  recorte (x0, y0, ancho, alto) en px originales o None, reduccion]
# 40x: planos 1-24 porque la muestra se movio despues del plano 24 (igual que el modelo de Fiji).
# 10x: recorte alrededor del esferoide (el campo de 1024 px es casi todo fondo), dejando afuera la fibra
#      autofluorescente de arriba.
VOLUMENES = [
    ("40x", "transfectadas/1_01.oif.files", (1, 24), 0.19775, 1.0, "Esferoide transfectado 40x", None, 2),
    ("10x", "transfectadas/1.oif.files", (1, 26), 0.6204, 2.0, "Esferoide transfectado 10x", (320, 368, 448, 340), 1),
]
# [nombre, canal Olympus, fraccion del fondo difuso que se resta]
CANALES = [("dapi", 1, 0.9), ("gfp", 2, 0.6), ("wga", 3, 0.8)]
# Limpieza por plano: sigma del fondo difuso, sigma y cantidad del realce de bordes (en px ya reducidos)
LIMPIEZA = {"40x": (20, 1.5, 0.8), "10x": (15, 1.2, 1.2)}
# 10x: la fibra autofluorescente (solo DAPI) cruza las primeras filas del recorte; se borra de ese canal
FILAS_SIN_DAPI = {"10x": 30}


def gauss1d(s):
    r = int(3 * s + 0.5)
    x = np.arange(-r, r + 1)
    k = np.exp(-x ** 2 / (2 * s * s))
    return k / k.sum()


def blur(im, s):
    # gaussiano 2D separable con bordes reflejados (solo numpy)
    k = gauss1d(s)
    r = len(k) // 2
    p = np.pad(im, r, mode="reflect")
    fil = np.zeros((p.shape[0], im.shape[1]))
    for i, w in enumerate(k):
        fil += w * p[:, i:i + im.shape[1]]
    out = np.zeros(im.shape)
    for i, w in enumerate(k):
        out += w * fil[i:i + im.shape[0]]
    return out


def limpiar(vol, resta, s_fondo, s_nitidez, cantidad):
    """Por plano: resta el fondo difuso (luz fuera de foco) y realza bordes (unsharp mask)."""
    res = []
    for im in vol:
        im = np.clip(im - resta * blur(im, s_fondo), 0, None)
        im = im + cantidad * (im - blur(im, s_nitidez))
        res.append(np.clip(im, 0, None))
    return np.stack(res)


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
    for nombre, c, resta in CANALES:
        planos = []
        for z in range(z0, z1 + 1):
            im = leer_tif(os.path.join(d, "s_C%03dZ%03d.tif" % (c, z)))
            if recorte:
                x0, y0, w, h = recorte
                im = im[y0:y0 + h, x0:x0 + w]
            im = im.reshape(im.shape[0] // r, r, im.shape[1] // r, r).mean(axis=(1, 3))
            planos.append(im)
        vol = np.stack(planos)  # z, y, x
        lo = np.quantile(vol[::2, ::3, ::3], 0.05)
        vol = limpiar(vol - lo, resta, *LIMPIEZA[vid])
        if nombre == "dapi" and vid in FILAS_SIN_DAPI:
            vol[:, :FILAS_SIN_DAPI[vid], :] = 0
        hi = np.quantile(vol[::2, ::3, ::3], 0.999)
        v8 = np.clip(vol / max(hi, 1) * 255, 0, 255).astype(np.uint8)
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
