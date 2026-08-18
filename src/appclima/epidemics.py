"""Catálogo curado de epidemias y pandemias históricas.

**Este módulo es distinto a todo lo demás del proyecto: no viene de una API.**

Se buscó una. No existe ninguna abierta con datos históricos de pandemias:

  - WHO GHO (OData, sin key) sirve indicadores sanitarios modernos por país,
    no eventos históricos.
  - EM-DAT, la base de referencia internacional, cubre epidemias desde 1900
    pero exige registro y su licencia es CC BY-NC, sin API pública.
  - ReliefWeb cubre desde 1981 y ahora exige un `appname` aprobado a mano.
  - Para la peste negra o la plaga de Justiniano simplemente no hay base de
    datos: hay historiografía.

Así que esto es un catálogo curado, con la misma disciplina que el catálogo de
ciudades: pocos registros, explícitos, versionados y auditables.

**Por qué todo son rangos y no cifras.** Las estimaciones de muertes de la peste
negra van de 75 a 200 millones. Las de la gripe de 1918, de 17 a 100 millones.
La plaga de Justiniano lleva una década en revisión y hay historiadores que
defienden que su impacto fue un orden de magnitud menor de lo que se creía.

En un dataset así, **el ancho del rango es tanto dato como el propio número**.
Guardar un punto medio y presentarlo como hecho sería el error más grave que se
puede cometer con esta información. Por eso cada registro lleva rango, nivel de
confianza y fuente, y por eso `deaths_low`/`deaths_high` no tienen valor por
defecto: si no se sabe, se queda nulo.

Cómo interpretar `estimate_confidence`:

  alta  — registro moderno con vigilancia epidemiológica (COVID, VIH, H1N1)
  media — estimación histórica con consenso razonable y rango acotado
  baja  — cifras muy disputadas entre historiadores; el rango es orientativo
"""

from __future__ import annotations

from appclima.schemas.disasters import HistoricalEpidemic

EPIDEMICS: list[HistoricalEpidemic] = [
    # ── Antigüedad ────────────────────────────────────────────────────────
    HistoricalEpidemic(
        id="plaga-de-atenas",
        name="Plaga de Atenas",
        pathogen="Desconocido (se ha propuesto tifus o fiebre tifoidea)",
        disease="Desconocida",
        start_year=-430, end_year=-426,
        deaths_low=50_000, deaths_high=100_000,
        regions="Atenas y el Ática",
        estimate_confidence="baja",
        source="Tucídides; estimaciones modernas sobre población ateniense",
        note=(
            "El agente causante sigue sin identificarse. El rango no sale solo "
            "de la tasa de mortalidad estimada (25-35%) sino también de que la "
            "propia población del Ática en el siglo V a.C. es incierta: la "
            "incertidumbre se multiplica, no se promedia."
        ),
    ),
    HistoricalEpidemic(
        id="peste-antonina",
        name="Peste Antonina",
        pathogen="Probablemente viruela",
        disease="Viruela (probable)",
        start_year=165, end_year=180,
        deaths_low=5_000_000, deaths_high=10_000_000,
        regions="Imperio romano",
        estimate_confidence="baja",
        source="Estimaciones historiográficas sobre demografía romana",
    ),
    HistoricalEpidemic(
        id="peste-de-cipriano",
        name="Peste de Cipriano",
        pathogen="Desconocido",
        disease="Desconocida",
        start_year=249, end_year=262,
        deaths_low=1_000_000, deaths_high=5_000_000,
        regions="Imperio romano",
        estimate_confidence="baja",
        source="Fuentes tardorromanas; cifras muy inciertas",
    ),
    HistoricalEpidemic(
        id="plaga-de-justiniano",
        name="Plaga de Justiniano",
        pathogen="Yersinia pestis",
        disease="Peste bubónica",
        start_year=541, end_year=549,
        deaths_low=15_000_000, deaths_high=100_000_000,
        regions="Imperio bizantino, Mediterráneo, Oriente Próximo",
        estimate_confidence="baja",
        source="Estimaciones clásicas; revisadas a la baja desde 2019",
        note=(
            "El rango es enorme a propósito. Investigación reciente (Mordechai "
            "et al.) cuestiona el impacto demográfico tradicionalmente "
            "atribuido. Es el registro más disputado del catálogo."
        ),
    ),

    # ── Peste negra y edad moderna ────────────────────────────────────────
    HistoricalEpidemic(
        id="peste-negra",
        name="Peste negra",
        pathogen="Yersinia pestis",
        disease="Peste bubónica y neumónica",
        start_year=1346, end_year=1353,
        deaths_low=75_000_000, deaths_high=200_000_000,
        regions="Europa, Norte de África, Oriente Próximo, Asia Central",
        estimate_confidence="media",
        source="Consenso historiográfico; ~30-60% de la población europea",
        note="La mayor mortalidad relativa documentada de la historia humana.",
    ),
    HistoricalEpidemic(
        id="viruela-americas",
        name="Viruela en América",
        pathogen="Variola major",
        disease="Viruela",
        start_year=1520, end_year=1600,
        deaths_low=25_000_000, deaths_high=56_000_000,
        regions="América, tras el contacto europeo",
        estimate_confidence="baja",
        source="Estimaciones de colapso demográfico americano",
        note=(
            "Solapa con cocoliztli y otras epidemias del mismo periodo: las "
            "cifras NO deben sumarse sin más."
        ),
    ),
    HistoricalEpidemic(
        id="cocoliztli-1545",
        name="Epidemia de cocoliztli",
        pathogen="Posiblemente Salmonella enterica Paratyphi C",
        disease="Fiebre hemorrágica",
        start_year=1545, end_year=1548,
        deaths_low=5_000_000, deaths_high=15_000_000,
        regions="Nueva España (actual México)",
        estimate_confidence="baja",
        source="ADN antiguo de Teposcolula-Yucundaa; cifras estimadas",
    ),
    HistoricalEpidemic(
        id="gran-peste-de-londres",
        name="Gran peste de Londres",
        pathogen="Yersinia pestis",
        disease="Peste bubónica",
        start_year=1665, end_year=1666,
        deaths_low=70_000, deaths_high=100_000,
        regions="Londres",
        estimate_confidence="media",
        source="Registros parroquiales de mortalidad de Londres",
        note="Aprox. una cuarta parte de la población de la ciudad.",
    ),

    # ── Siglos XIX y XX ───────────────────────────────────────────────────
    HistoricalEpidemic(
        id="tercera-pandemia-peste",
        name="Tercera pandemia de peste",
        pathogen="Yersinia pestis",
        disease="Peste bubónica",
        start_year=1855, end_year=1960,
        deaths_low=12_000_000, deaths_high=15_000_000,
        regions="China e India principalmente; alcance global",
        estimate_confidence="media",
        source="Registros coloniales de la India británica y China",
    ),
    HistoricalEpidemic(
        id="gripe-rusa-1889",
        name="Gripe rusa",
        pathogen="Virus gripal (subtipo discutido)",
        disease="Gripe",
        start_year=1889, end_year=1890,
        deaths_low=300_000, deaths_high=1_000_000,
        regions="Global",
        estimate_confidence="baja",
        source="Estadísticas de mortalidad europeas de la época",
    ),
    HistoricalEpidemic(
        id="sexta-pandemia-colera",
        name="Sexta pandemia de cólera",
        pathogen="Vibrio cholerae",
        disease="Cólera",
        start_year=1899, end_year=1923,
        deaths_low=800_000, deaths_high=1_500_000,
        regions="India, Oriente Próximo, Rusia, Norte de África",
        estimate_confidence="media",
        source="Registros sanitarios coloniales",
    ),
    HistoricalEpidemic(
        id="gripe-1918",
        name="Pandemia de gripe de 1918",
        pathogen="Virus gripal A/H1N1",
        disease="Gripe",
        start_year=1918, end_year=1920,
        deaths_low=17_400_000, deaths_high=100_000_000,
        regions="Global",
        estimate_confidence="media",
        source="Estimaciones revisadas de mortalidad global",
        note=(
            "La cifra de 50 millones que se repite en prensa es un punto medio "
            "de un rango que va de 17 a 100. El rango es el dato."
        ),
    ),
    HistoricalEpidemic(
        id="tifus-rusia-1918",
        name="Epidemia de tifus en Rusia",
        pathogen="Rickettsia prowazekii",
        disease="Tifus epidémico",
        start_year=1918, end_year=1922,
        deaths_low=2_000_000, deaths_high=3_000_000,
        regions="Rusia y Europa del Este",
        estimate_confidence="baja",
        source="Estimaciones sobre el periodo de la guerra civil rusa",
    ),
    HistoricalEpidemic(
        id="gripe-asiatica-1957",
        name="Gripe asiática",
        pathogen="Virus gripal A/H2N2",
        disease="Gripe",
        start_year=1957, end_year=1958,
        deaths_low=1_000_000, deaths_high=4_000_000,
        regions="Global",
        estimate_confidence="media",
        source="Estimaciones retrospectivas de la OMS",
    ),
    HistoricalEpidemic(
        id="gripe-hong-kong-1968",
        name="Gripe de Hong Kong",
        pathogen="Virus gripal A/H3N2",
        disease="Gripe",
        start_year=1968, end_year=1970,
        deaths_low=1_000_000, deaths_high=4_000_000,
        regions="Global",
        estimate_confidence="media",
        source="Estimaciones retrospectivas de la OMS",
    ),
    HistoricalEpidemic(
        id="septima-pandemia-colera",
        name="Séptima pandemia de cólera",
        pathogen="Vibrio cholerae El Tor",
        disease="Cólera",
        start_year=1961, end_year=None,
        deaths_low=None, deaths_high=None,
        regions="Asia, África, América Latina",
        estimate_confidence="media",
        source="OMS; vigilancia continua",
        note=(
            "Sigue en curso desde 1961. Sin cifra acumulada fiable: la "
            "notificación varía enormemente entre países y décadas."
        ),
    ),

    # ── Era moderna, con vigilancia epidemiológica ────────────────────────
    HistoricalEpidemic(
        id="vih-sida",
        name="Pandemia de VIH/sida",
        pathogen="VIH-1 y VIH-2",
        disease="Sida",
        start_year=1981, end_year=None,
        deaths_low=40_000_000, deaths_high=48_000_000,
        regions="Global; mayor impacto en África subsahariana",
        estimate_confidence="alta",
        source="ONUSIDA, muertes acumuladas notificadas",
        note="Sigue en curso. La cifra es acumulada, no anual.",
    ),
    HistoricalEpidemic(
        id="sars-2002",
        name="Brote de SARS",
        pathogen="SARS-CoV-1",
        disease="Síndrome respiratorio agudo grave",
        start_year=2002, end_year=2004,
        deaths_low=774, deaths_high=774,
        regions="Asia oriental, Canadá",
        estimate_confidence="alta",
        source="OMS, recuento final de casos",
        note=(
            "Rango de ancho cero: es un recuento cerrado, no una estimación. "
            "Sirve de contraste con los registros históricos."
        ),
    ),
    HistoricalEpidemic(
        id="gripe-a-2009",
        name="Pandemia de gripe A (H1N1)",
        pathogen="Virus gripal A/H1N1pdm09",
        disease="Gripe",
        start_year=2009, end_year=2010,
        deaths_low=151_700, deaths_high=575_400,
        regions="Global",
        estimate_confidence="alta",
        source="CDC, estimación de mortalidad respiratoria del primer año",
        note=(
            "Ejemplo perfecto de por qué importan los rangos: las muertes "
            "confirmadas por laboratorio fueron ~18.500, casi treinta veces "
            "menos que la estimación baja de exceso de mortalidad."
        ),
    ),
    HistoricalEpidemic(
        id="mers",
        name="MERS",
        pathogen="MERS-CoV",
        disease="Síndrome respiratorio de Oriente Medio",
        start_year=2012, end_year=None,
        deaths_low=900, deaths_high=1_000,
        regions="Península arábiga; brote en Corea del Sur en 2015",
        estimate_confidence="alta",
        source="OMS, vigilancia continua",
    ),
    HistoricalEpidemic(
        id="ebola-africa-occidental",
        name="Epidemia de ébola en África occidental",
        pathogen="Virus del Ébola (cepa Zaire)",
        disease="Enfermedad por virus del Ébola",
        start_year=2014, end_year=2016,
        deaths_low=11_325, deaths_high=11_325,
        regions="Guinea, Liberia, Sierra Leona",
        estimate_confidence="alta",
        source="OMS, informe final de situación",
    ),
    HistoricalEpidemic(
        id="covid-19",
        name="Pandemia de COVID-19",
        pathogen="SARS-CoV-2",
        disease="COVID-19",
        start_year=2019, end_year=None,
        deaths_low=7_000_000, deaths_high=28_000_000,
        regions="Global",
        estimate_confidence="alta",
        source="OMS: muertes notificadas (~7M) y exceso de mortalidad estimado",
        note=(
            "El rango separa dos cosas distintas: el extremo bajo son muertes "
            "confirmadas y notificadas; el alto es exceso de mortalidad "
            "estimado para 2020-2021. No es incertidumbre histórica, es la "
            "diferencia entre lo que se contó y lo que ocurrió."
        ),
    ),
]

BY_ID: dict[str, HistoricalEpidemic] = {e.id: e for e in EPIDEMICS}
