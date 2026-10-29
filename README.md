# Esferoides HT22 transfectados con M6a-GFP · Grupo 8

Página del TP de Biología Celular 2026 (EByN, UNSAM): modelo 3D del esferoide (confocal 40x y 10x) e informe corregido.

- `index.html`: portada con los botones.
- `modelo.html?v=40x` / `?v=10x`: visor 3D (three.js, ray marching en WebGL2). WGA en rojo, M6a-GFP en verde, DAPI en azul (arranca apagado).
- `data/`: volúmenes en 8 bits comprimidos con gzip, uno por canal. Se generan con `scripts/preparar_datos.py` a partir de los `.oif` originales (40x: planos 1-24, reducido a la mitad; 10x: recorte alrededor del esferoide).
- `Informe_Esferoides_HT22_Grupo8.pdf`: informe corregido.
