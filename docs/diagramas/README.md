# Diagramas editables

El diagrama principal de la arquitectura está en `arquitectura.mmd`, formato Mermaid editable.

Puedes visualizarlo en:

- VS Code con una extensión Mermaid.
- GitHub, al incluir el diagrama en Markdown.
- Mermaid Live Editor, copiando el contenido sin subir datos sensibles.

La exportación PNG/PDF para el paper se genera solo después de aprobar la versión editable.

## Topología en Cisco Packet Tracer

- `topologia-empresa.pkt`: proyecto de Packet Tracer 9.0.1 (se abre con *File → Open*).
- `topologia-empresa.png`: figura recortada que usa el paper (`\includegraphics{topologia-empresa.png}`; el `.tex` declara dónde buscarlo con `\graphicspath`).
- `topologia-empresa-captura.png`: captura sin recortar del lienzo.
- `pruebas-topologia.md`: equipos, direccionamiento, las 10 pruebas de conectividad, configuración de `R-EDGE` y limitaciones.

Si se regenera la figura con el servidor MCP, este guarda en la carpeta `PacketTracerMCP` de su directorio de usuario y hay que copiar los archivos aquí.
