"""API HTTP sobre el warehouse.

Esta capa existe por una razón estratégica, no técnica: **es la frontera que
hace que el salto de web a iOS cueste solo trabajo de interfaz.**

Si la web llamara directamente a Open-Meteo y USGS desde el navegador, toda la
lógica de datos viviría dentro de componentes de React y habría que reescribirla
entera para una app nativa. Con la API en medio, el cliente de iOS consume
exactamente los mismos endpoints y no se reimplementa nada.

Beneficio secundario, y no pequeño: los tokens (eBird hoy, FIRMS u OpenAQ
mañana) se quedan en el servidor. Una web que llama a APIs con key desde el
navegador expone esa key a cualquiera que abra las herramientas de desarrollo.
"""
