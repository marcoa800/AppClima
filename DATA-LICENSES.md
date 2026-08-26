# Licencias de los datos

`LICENSE` cubre **el código** de este repositorio y es MIT: haz con él lo que
quieras. Este fichero es lo otro, y es lo que de verdad puede meterte en un lío.

**Los datos no son míos y no los relicencio.** Cada fuente conserva la suya, y
varias son más restrictivas que MIT. Si tomas este código y consultas las mismas
APIs, esas condiciones te aplican a ti directamente: son de ellos, no mías, y yo
no puedo levantártelas.

> Este fichero se mantiene a mano y por eso puede quedarse atrás. La fuente de
> verdad es `src/appclima/attribution.py`, que se versiona, se testea y se sirve
> en `/sources`. Un test recorre el paquete de conectores y falla si alguno no
> tiene entrada de licencia — se añadió después de descubrir que OpenDengue
> llevaba varios despliegues publicándose sin atribuir.

## Lo que condiciona qué puedes hacer

| Fuente | Uso comercial | Detalle |
|---|---|---|
| **Open-Meteo** | ❌ Prohibido | El plan gratuito excluye el uso comercial, y su definición **incluye publicidad y patrocinios**. Monetizar de cualquier forma obliga a plan de pago (~29 €/mes) o a autoalojar su servidor, que es código abierto. Es la razón de que este proyecto sea y siga siendo gratuito. |
| **eBird** | ⚠️ Requiere permiso | Del Cornell Lab of Ornithology. |
| **GBIF** | ⚠️ Caso por caso | Algunos datasets subyacentes son CC BY-NC. |
| USGS, NOAA NCEI, IBTrACS, NOAA CPC | ✅ Dominio público | |
| Banco Mundial | ✅ CC BY 4.0 | Con atribución. |
| **OpenDengue** | ✅ CC BY 4.0 | Con **cita formal obligatoria**, ver abajo. |

## Citas obligatorias

**OpenDengue**

> Clarke J, Lim A, Gupte P, Pigott DM, van Panhuis WG, Brady OJ. A global
> dataset of publicly available dengue case count data. *Scientific Data* 11,
> 296 (2024).

Para Perú, lo que hay dentro son los boletines del CDC-MINSA que alimentan la
sala situacional de metaxénicas.

**Open-Meteo**

> Datos meteorológicos de Open-Meteo.com (CC BY 4.0), basados en el reanálisis
> ERA5 de Copernicus / ECMWF.

**Banco Mundial**

> World Development Indicators, Banco Mundial (CC BY 4.0).

## Una cita que está incompleta, y conviene decirlo

Se usó la API de búsqueda de GBIF con facetas, que devuelve recuentos y no
registros, así que GBIF no emite DOI. Una cita formal exige la API de descargas
—cuenta gratuita— y da un DOI citable con la lista exacta de datasets y
publicadores. Es lo que habría que hacer antes de publicar cualquier resultado
basado en GBIF.
