"""Esquema de fenología: cuándo llegan las aves migratorias.

Este es el análisis que motivó el proyecto y el único que puede responder a
"¿llegan las aves antes que hace treinta años?". eBird no puede: devuelve solo
la observación más reciente por especie. GBIF sí, porque agrega los registros
históricos de miles de instituciones.

**Diseño obligado por dos límites de la fuente:**

1. **17,5 millones de registros para una sola especie.** Paginar está descartado
   (el buscador corta en 100.000 de desplazamiento). La salida es la API de
   FACETAS: una petición devuelve el recuento por mes sin descargar ni un solo
   registro. De 32 páginas a 1 llamada.

2. **El esfuerzo de observación varía brutalmente entre años.** En la caja de
   Madrid la golondrina tiene 586 registros en 1990, 6.957 en 2000, 1.530 en
   2015 y 9.582 en 2024. Contar registros mediría cuánta gente salió al campo,
   exactamente el sesgo que ya cuantificamos con eBird (68% de la varianza).

ADVERTENCIA APRENDIDA A GOLPES: normalizar dentro del año NO basta. Se midió un
adelanto de 9,3 días por década en la golondrina, que resultó ser artefacto: la
proporción de registros de marzo pasó del 1,67% al 5,20% entre 1995 y 2024, y en
Madrid del 0,44% al 10,47% — un factor de 24. No es que las aves lleguen antes,
es que la gente empezó a mirar antes.

Por eso existen las ESPECIES CONTROL: residentes que no migran. Su percentil
debería ser plano; lo que se mueva en ellas es sesgo puro, y se resta a las
migratorias. Es un diseño de diferencias-en-diferencias.

La normalización dentro del año (abajo) sigue siendo necesaria, pero solo
corrige el volumen total, no el reparto estacional del esfuerzo.

La solución al punto 2 es normalizar DENTRO de cada año: en lugar de recuentos
se usa el día del año en que se acumula el 10% de los registros anuales. Si el
esfuerzo total de un año se duplica, numerador y denominador se duplican y el
percentil no se mueve. Lo único que se asume es que el patrón estacional del
esfuerzo es estable entre años, que es mucho más débil que asumir esfuerzo
constante.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PhenologyYear(BaseModel):
    """Recuentos mensuales de una especie en una zona durante un año."""

    model_config = ConfigDict(extra="forbid")

    species_key: int = Field(description="taxonKey de GBIF")
    species_name: str
    common_name: str
    location_id: str = Field(description="Ciudad ancla en cuyo entorno se buscó")
    bbox_degrees: float = Field(description="Semilado de la caja de búsqueda")

    is_control: bool = Field(
        default=False,
        description=(
            "Especie RESIDENTE, usada como control del sesgo de observación. "
            "No migra, así que su 'fecha de llegada' debería ser plana en el "
            "tiempo: cualquier tendencia que muestre es artefacto del "
            "observador y hay que restarla a las migratorias."
        ),
    )

    year: int
    total_records: int = Field(description="Registros del año en la caja")

    # Recuento por mes. Doce columnas explícitas en lugar de una lista porque
    # Parquet las almacena mucho mejor y DuckDB las consulta sin desanidar.
    m01: int = 0
    m02: int = 0
    m03: int = 0
    m04: int = 0
    m05: int = 0
    m06: int = 0
    m07: int = 0
    m08: int = 0
    m09: int = 0
    m10: int = 0
    m11: int = 0
    m12: int = 0
