# Esferoides HT22 transfectados con M6a-GFP · Grupo 8

Página del TP de Biología Celular 2026 (EByN, UNSAM): modelo 3D del esferoide (confocal 40x y 10x) e informe corregido.

- `index.html`: portada estilo terminal; el esferoide en caracteres (`planos_z.js`) recorre los planos del stack.
- `integrantes.html`: lista desplegable; los datos de cada uno (foto, descripción, mail, CV, LinkedIn) se completan en el arreglo `INTEGRANTES`.
- `modelo.html?v=40x` / `?v=10x`: visor 3D (three.js, ray marching en WebGL2). WGA en rojo, M6a-GFP en verde, DAPI en azul (arranca apagado). La barra de carga mide los bytes descargados de verdad.
- `data/`: volúmenes en 8 bits comprimidos con gzip, uno por canal. Se generan con `scripts/preparar_datos.py` a partir de los `.oif` originales (40x: planos 1-24, reducido a la mitad; 10x: recorte alrededor del esferoide).
- `Informe_Esferoides_HT22_Grupo8.pdf`: informe corregido.
