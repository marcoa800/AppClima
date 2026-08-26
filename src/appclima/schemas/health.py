"""Esquemas de vigilancia epidemiológica.

El dengue es, de todas las enfermedades con vigilancia sistemática, **la más
determinada por el clima**. No es una correlación de sobremesa: la cadena
causal está medida en laboratorio y cada eslabón depende de la temperatura.

  1. El mosquito *Aedes aegypti* necesita agua estancada para criar, así que
     la lluvia crea criaderos — y la sequía también, porque la gente almacena
     agua en recipientes destapados.
  2. El desarrollo de larva a adulto tarda ~15 días a 20 °C y ~7 a 30 °C.
  3. El **período de incubación extrínseco** —lo que tarda el virus en llegar
     a las glándulas salivales del mosquito y hacerlo infectante— cae de unos
     15 días a 25 °C a unos 7 a 30 °C. Por debajo de ~18 °C prácticamente no
     se completa antes de que el mosquito muera.

El tercer punto es el que hace del dengue un problema climático y no solo
tropical: la transmisión no decae suavemente con el frío, se **corta**. Por eso
existe un límite de altitud, y por eso ese límite se mueve cuando sube la
temperatura.

De ahí sale también el retardo que hay que respetar al modelar: entre las
condiciones climáticas y el caso notificado median el ciclo del mosquito, la
incubación extrínseca, la incubación humana (4-10 días) y el retraso de
notificación. Suman del orden de **4 a 12 semanas**. Correlacionar clima y
casos en la misma semana es buscar la causa después del efecto.

Fuente: OpenDengue (London School of Hygiene & Tropical Medicine), que reúne y
homogeneiza los boletines nacionales de vigilancia — para Perú, los del
CDC-MINSA que alimentan la sala situacional. CC BY 4.0.

https://opendengue.org · https://github.com/OpenDengue/master-repo
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DengueWeek(BaseModel):
    """Casos de dengue en una unidad administrativa durante un período.

    Grano: (`uuid`), que OpenDengue construye como
    fuente-territorio-año-período y es único por fila publicada.

    `cases` es float y no int a propósito. Cuando OpenDengue tiene que repartir
    un total mensual entre semanas, o un total departamental entre provincias,
    el reparto produce fracciones. Redondear al ingerir destruiría información
    y haría que las sumas no cuadrasen con el boletín original.
    """

    model_config = ConfigDict(extra="forbid")

    uuid: str = Field(description="Clave natural de OpenDengue")

    country_name: str
    iso3: str | None = Field(default=None, description="ISO 3166-1 alfa-3")
    adm_1_name: str | None = Field(default=None, description="Departamento/estado")
    adm_2_name: str | None = Field(default=None, description="Provincia/municipio")
    full_name: str = Field(description="Jerarquía completa, tal como la publica la fuente")

    period_start: date
    period_end: date
    year: int

    cases: float | None = None

    # Mezclar definiciones de caso es el equivalente epidemiológico de mezclar
    # magnitudes sísmicas de distinta completitud: "sospechosos" y "confirmados"
    # no son la misma serie, y un país que pasa de una a otra genera un salto
    # que parece un brote. Se conserva la etiqueta para poder filtrar por ella.
    case_definition: str | None = Field(
        default=None, description="Confirmed | Suspected | Probable and confirmed…"
    )

    # Admin0/1/2 y Week/Month/Year. Una misma unidad puede aparecer con varias
    # resoluciones: sumarlas contaría los mismos casos dos veces.
    spatial_res: str = Field(description="Admin0 | Admin1 | Admin2")
    temporal_res: str = Field(description="Week | Month | Year")
