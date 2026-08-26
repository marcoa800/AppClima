"""Catálogo de resultados NULOS: lo que se buscó y no está.

**Esta es la parte del proyecto que no tiene ninguna otra web del tiempo.**

Hay mil sitios con gráficas de temperatura. Ninguno dice "medimos esto, salió
que no, y aquí está el número". Publicar los nulos no es humildad decorativa:
es lo que convierte un conjunto de gráficas en un trabajo de análisis, porque
demuestra que las afirmaciones que SÍ se hacen pasaron por el mismo filtro.

Cada entrada exige cuatro cosas, y si falta alguna no entra:

  - la afirmación que se contrastó, en los términos en que suele oírse
  - el estadístico concreto, con su n y su umbral
  - por qué el resultado es sólido y no simple falta de datos
  - qué se aprende del nulo, que casi siempre es más que del hallazgo

Muchos de estos salieron de verificación adversarial: un agente encontraba
señal y otro, con el mandato explícito de refutarla, la desmontaba.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Strength = Literal["definitivo", "sólido", "provisional"]


class NullFinding(BaseModel):
    """Algo que se buscó, se midió bien, y no está."""

    model_config = ConfigDict(extra="forbid")

    id: str
    claim: str = Field(description="La afirmación contrastada, tal como se oye")
    verdict: str = Field(description="Qué salió, en una frase")
    statistic: str = Field(description="La cifra concreta con su n y umbral")
    why_solid: str = Field(description="Por qué es un nulo y no falta de datos")
    lesson: str = Field(description="Qué se aprende")
    strength: Strength
    domain: str


NULL_FINDINGS: list[NullFinding] = [
    NullFinding(
        id="dengue-umbral-termico",
        domain="salud",
        claim="Existe una temperatura por debajo de la cual el dengue no se "
              "transmite, y basta con vigilar el termómetro para saber qué "
              "ciudades entran en riesgo.",
        verdict="El umbral nítido desapareció al arreglar el termómetro. La "
                "temperatura media no decide el borde.",
        statistic="Con el archivo original, las 6 provincias más cálidas de 12 "
                  "sumaban 309.765 casos y las 6 más frías seis, con el corte "
                  "entre Lima (18,9 °C) y Tacna (18,0 °C); test exacto "
                  "1/C(12,6) = 0,0011. Con un único reanálisis (ERA5), Lima y "
                  "Tacna están ambas a 18,88 °C: 32.466 casos frente a 0.",
        why_solid="El fallo no fue de muestra sino de instrumento. Open-Meteo, "
                  "sin fijar el modelo, sirve ERA5 hasta 2016 y el IFS de "
                  "ECMWF desde 2017; en Tacna esa costura vale 2,44 °C y la "
                  "hacía parecer 2,4 °C más fría de lo que es. Con la "
                  "procedencia homogénea, las dos ciudades coinciden en "
                  "temperatura y difieren en todo lo demás.",
        lesson="Un resultado limpio con un mecanismo elegante detrás es "
               "justo el que menos se audita. El período de incubación "
               "extrínseco predice un corte cerca de 18 °C, la coincidencia "
               "con el dato parecía validación externa, y era el sesgo del "
               "reanálisis. La temperatura resulta necesaria pero no "
               "suficiente: por debajo de 15 °C no hay transmisión en ninguna "
               "provincia, pero por encima no basta con el termómetro.",
        strength="sólido",
    ),
    NullFinding(
        id="dengue-clima-retardado",
        domain="salud",
        claim="El calor de hace 4-12 semanas predice los casos de dengue de "
              "esta semana, en cualquier provincia con transmisión.",
        verdict="Nulo en cuatro de seis provincias. Sobrevive en dos, y "
                "justamente NO en la de mayor carga.",
        statistic="6 provincias × 21 retardos × 2 variables sobre ~935 semanas. "
                  "Pasan Bonferroni y la validación temporal solo Trujillo "
                  "(retardo 4 semanas, r = 0,650, 42% de varianza; entreno "
                  "≤2016 r = 0,507 → prueba ≥2017 r = 0,759) y Chiclayo "
                  "(retardo 3, r = 0,476; 0,370 → 0,551). Piura, con 98.668 "
                  "casos, se desmorona fuera de muestra: 0,501 → 0,085. "
                  "Iquitos y Pucallpa, nada. La lluvia no pasa en ninguna.",
        why_solid="El diseño compara cada provincia consigo misma, así que "
                  "pobreza, altitud y sistema sanitario quedan controlados. "
                  "Series desestacionalizadas contra la media de esa semana "
                  "del año, casos en log(1+x), n efectivo corregido por una "
                  "autocorrelación de 0,90-0,96 —que reduce 935 semanas a "
                  "37-101 datos independientes— y partición temporal, nunca "
                  "aleatoria: repartir semanas al azar mediría persistencia.",
        lesson="El nulo no es del mecanismo sino de su generalidad. Donde la "
               "temperatura funciona es donde es limitante: Trujillo y "
               "Chiclayo rondan los 21 °C, cerca del margen de transmisión. "
               "Piura está a 24 °C con casos el 62% de las semanas —"
               "hiperendémica y saturada— y ahí el termómetro ya no explica "
               "nada. Un modelo climático de dengue no se puede desplegar "
               "igual en todas partes: sirve en el borde, no en el núcleo. "
               "Ojo además con que el retardo se eligió mirando los datos; "
               "lo que lo salva es que aguante con el retardo ya fijado.",
        strength="provisional",
    ),
    NullFinding(
        id="clima-sismico",
        domain="sismos",
        claim="«Hacía tiempo de terremotos»: la presión atmosférica o el calor "
              "anuncian los sismos.",
        verdict="No hay ninguna relación práctica.",
        statistic="r = 0,012 entre sismos diarios en 500 km y presión "
                  "atmosférica, sobre 87.654 días-ciudad. Explica el 0,014% de "
                  "la varianza. Tokio, con la mayor muestra (1.903 sismos), da "
                  "r = −0,002.",
        why_solid="La muestra es enorme y el resultado es consistente ciudad a "
                  "ciudad. Físicamente era lo esperado: los sismos se originan "
                  "por esfuerzo tectónico acumulado durante siglos, y las "
                  "variaciones de presión son cinco órdenes de magnitud "
                  "menores que lo que rompe una falla.",
        lesson="Con n = 87.654 el umbral de significación cae a r = 0,0066, así "
               "que una correlación irrelevante sale «estadísticamente "
               "significativa». La significación responde a «¿es distinto de "
               "cero?», no a «¿importa?». Por eso la varianza explicada va "
               "siempre al lado del test.",
        strength="definitivo",
    ),
    NullFinding(
        id="fenologia-aves",
        domain="aves",
        claim="Las aves migratorias llegan cada vez antes por el calentamiento.",
        verdict="No se puede detectar con datos de ciencia ciudadana. El "
                "«adelanto» medido era del observador, no del ave.",
        statistic="La golondrina daba −9,3 días/década. Pero las especies "
                  "CONTROL —gorrión y carbonero, que no migran y están todo el "
                  "año— daban −8,9 y −12,2. Tras diferencias en diferencias "
                  "queda +1,2 días/década, no significativo.",
        why_solid="El placebo cierra el caso: aplicando la misma tubería a un "
                  "control contra el otro control sale ±2,5 a 5,6 días/década "
                  "con p = 0,033. El suelo de ruido del método es tan grande "
                  "como cualquier residuo que quede.",
        lesson="La proporción de registros de marzo pasó del 1,67% al 5,20% "
               "entre 1995 y 2024, y en Madrid del 0,44% al 10,47%. No es que "
               "las aves lleguen antes: es que la gente empezó a mirar antes. "
               "Sin especie control, esto se habría publicado como hallazgo.",
        strength="definitivo",
    ),
    NullFinding(
        id="temporada-ciclones",
        domain="ciclones",
        claim="La temporada de huracanes se está adelantando y alargando.",
        verdict="El calendario no se ha movido entre 1980 y 2023.",
        statistic="La mediana de la temporada se desplaza −0,017 meses por "
                  "década, o sea medio día por década. r = −0,07, p = 0,66. La "
                  "duración efectiva tampoco cambia (−0,08 meses/década, "
                  "p = 0,52).",
        why_solid="Se midió sobre proporciones acumuladas DENTRO de cada "
                  "temporada, no sobre recuentos: si una temporada es más "
                  "activa, los recuentos suben en todos los meses sin que el "
                  "calendario se mueva. Las cinco primeras temporadas tienen "
                  "mediana en 8,30 y las cinco últimas en 8,27.",
        lesson="La climatología es notablemente estable: el 25% del ACE se "
               "acumula hacia el 2 de agosto, la mediana el 7 de septiembre y "
               "el 75% el 7 de octubre, año tras año.",
        strength="sólido",
    ),
    NullFinding(
        id="ace-global",
        domain="ciclones",
        claim="Hay más ciclones tropicales que antes.",
        verdict="La energía ciclónica global no muestra tendencia en 45 años.",
        statistic="r = −0,03 entre año y ACE global, 1980-2024. Los huracanes "
                  "mayores dan r = 0,29 frente a un umbral de 0,292: justo en "
                  "la línea, tan al filo que una temporada más podría "
                  "voltearlo.",
        why_solid="La ventana arranca en 1980 precisamente porque antes de la "
                  "cobertura satelital global los ciclones que no tocaban "
                  "tierra no se observaban. Una serie desde 1842 muestra una "
                  "subida espectacular que mide capacidad de observación.",
        lesson="Coincide con la literatura: sin señal clara en frecuencia "
               "total, indicios débiles de mayor proporción de tormentas "
               "intensas. Por eso la gráfica no dibuja recta de tendencia — "
               "trazarla invitaría a leer una pendiente que los datos no "
               "sostienen.",
        strength="sólido",
    ),
    NullFinding(
        id="letalidad-por-evento",
        domain="desastres",
        claim="Los desastres son cada vez menos letales gracias a las alertas "
              "tempranas.",
        verdict="La letalidad POR EVENTO no ha bajado en un siglo. La mejora "
                "per cápita es aritmética del denominador.",
        statistic="Terremotos M≥7 con ≥100 muertos: mediana de 1.070 muertos "
                  "antes de 1960 y 844 después. p = 0,895, n = 154. La "
                  "pendiente de las muertes totales por década es +0,02 en "
                  "log10, no significativa; la de población, +0,06.",
        why_solid="Aguanta sin filtro de magnitud, con umbrales de 50 a 1.000 "
                  "muertos, en ventanas 1930-, 1940- y 1960-2019, y quitando "
                  "del top-1 al top-10 por muertes. Todos no significativos.",
        lesson="log10(muertes/millón) = log10(muertes) − log10(población). Con "
               "el numerador plano y la población multiplicada por 4,7, el 100% "
               "de la «mejora» viene del denominador. **Siempre que reportes "
               "una tasa, reporta numerador y denominador por separado.**",
        strength="sólido",
    ),
    NullFinding(
        id="anio-horrible",
        domain="multidominio",
        claim="Hay años malos en los que todo pasa a la vez.",
        verdict="Los dominios van cada uno a su aire. El «año horrible» no "
                "existe como estructura estadística.",
        statistic="Con 20.000 permutaciones: varianza del índice compuesto "
                  "p = 0,35, máximo p = 0,37, co-ocurrencia de extremos "
                  "p = 0,24. La mejor correlación cruzada entre dominios "
                  "explica el 0,3% de la varianza.",
        why_solid="Lo que parecía acoplamiento venía de contar dos veces el "
                  "mismo dominio: ACE global y huracanes mayores salen ambos "
                  "de IBTrACS y correlacionan a 0,772. Deduplicando a tres "
                  "dominios reales, ninguna correlación supera su umbral.",
        lesson="2004 encabeza el ranking por dos accidentes sin relación: el "
               "tsunami del Índico y una temporada ciclónica activa el mismo "
               "año. La memoria humana fabrica el patrón; los datos no.",
        strength="sólido",
    ),
    NullFinding(
        id="mes-que-mas-calienta",
        domain="clima",
        claim="El calentamiento se concentra en unos meses concretos.",
        verdict="Ningún mes se calienta significativamente más rápido que otro.",
        statistic="Las 12 ciudades se calientan a +0,605 °C/década. Las "
                  "pendientes por mes van de +0,29 (enero) a +0,93 "
                  "(noviembre), pero esa dispersión no supera el ruido bajo "
                  "permutación en bloque: p = 0,15.",
        why_solid="La correlación entre las pendientes mensuales de la primera "
                  "y la segunda mitad de la ventana es NEGATIVA (−0,30), que "
                  "es la firma exacta de un patrón inexistente: si el efecto "
                  "fuera real, las dos mitades coincidirían.",
        lesson="Alinear el hemisferio sur por estación local tampoco rescata "
               "nada: verano menos invierno da −0,145 °C/década con p = 0,38. "
               "Ni amplificación invernal ni veraniega.",
        strength="sólido",
    ),
    NullFinding(
        id="correlaciones-del-panel",
        domain="metodología",
        claim="Cruzando fuentes en un panel temporal aparecen relaciones "
              "nuevas.",
        verdict="El 92% de las correlaciones llamativas del panel mensual son "
                "falsas.",
        statistic="De 153 pares de columnas, 77 superan el umbral ingenuo de "
                  "0,065 y solo 6 sobreviven a corregir por autocorrelación, "
                  "estacionalidad, tendencia y ventana. Con Bonferroni quedan "
                  "2, y ambos son el mismo sismo contado dos veces.",
        why_solid="Cada corrección se aplicó en cascada y se verificó de forma "
                  "independiente. La víctima estrella pasa de r = +0,676 a "
                  "+0,284 y a p = 0,27 en el nulo por desplazamiento circular.",
        lesson="`bird_records` crece de 32.300 a 300.587 registros porque crece "
               "eBird, no porque crezcan las aves, y correlaciona con cualquier "
               "serie creciente. Su pareja con temperatura **cambia de signo** "
               "al destendenciar. La señal más fuerte del panel entero no es "
               "climática: es r(fuentes disponibles, año) = +0,903.",
        strength="definitivo",
    ),
    NullFinding(
        id="enso-ciclones-ciudad",
        domain="ciclones",
        claim="El Niño permite anticipar si un ciclón pasará cerca de tu "
              "ciudad.",
        verdict="Condicionar por fase ENSO es PEOR que la tasa base de cada "
                "ciudad.",
        statistic="Brier Skill Score = −3,2%. Y 14 de 15 combinaciones de "
                  "radio y esquema dan BSS negativo.",
        why_solid="La única positiva (+0,052) es una casilla de quince que no "
                  "se sostiene en radios vecinos. Manila y Tokio ni siquiera "
                  "son evaluables: tuvieron ciclón cerca las 45 temporadas.",
        lesson="ENSO SÍ modula la actividad por cuenca —r hasta +0,71 en el "
               "Pacífico Oeste— pero eso no se traduce en riesgo para una "
               "ciudad concreta. Un efecto real a escala de cuenca puede ser "
               "inútil a escala local.",
        strength="sólido",
    ),
    NullFinding(
        id="riesgo-calor-tendencia",
        domain="predicción",
        claim="Corregir la climatología por la tendencia de cada ciudad mejora "
              "el pronóstico de calor extremo.",
        verdict="Retenido. La mejora cae de +16,9% a +3,5% al medirla en cinco "
                "cortes en vez de uno, y el mecanismo declarado es falso.",
        statistic="Mediana de Brier Skill Score +3,5% sobre 5 cortes "
                  "temporales, con rango de +1,9% a +6,0%. Por debajo del "
                  "umbral de publicación del proyecto.",
        why_solid="Permutando las pendientes entre ciudades —dándole a Madrid "
                  "la tendencia de Tokio— el skill se mantiene. Y un "
                  "desplazamiento global arbitrario de +0,15 °C/año, ajustado a "
                  "nada, funciona MEJOR que las pendientes reales.",
        lesson="No estaba prediciendo: estaba corrigiendo un sesgo. La "
               "climatología de 2006-2018 está sistemáticamente por debajo del "
               "clima actual, y subir las probabilidades en la magnitud "
               "correcta basta para ganar skill sin saber nada de cada ciudad.",
        strength="sólido",
    ),
]

BY_ID: dict[str, NullFinding] = {n.id: n for n in NULL_FINDINGS}
