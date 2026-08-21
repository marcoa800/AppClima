"""Capa de transformación: bronze → silver → gold.

Los modelos son ficheros .sql numerados, uno por modelo, ejecutados en orden.
Es dbt sin dbt: misma disciplina (un modelo por fichero, dependencias
explícitas por orden, todo reconstruible desde cero) sin arrastrar 100 MB de
dependencias. Migrar a dbt después es mover los ficheros y añadir `ref()`.

Contrato de las tres capas:

  bronze — crudo, append-only, con duplicados. Nunca se toca.
  silver — limpio y deduplicado. NADA de lógica de negocio.
  gold   — agregados y features. Aquí sí van las decisiones analíticas.

Silver se materializa como TABLAS, no como vistas, y la razón es de portabilidad
más que de rendimiento. Una vista guarda su definición literal, y esa definición
contiene la ruta ABSOLUTA de los Parquet de bronze:

    read_parquet('/Users/marco/AppClima/data/bronze/usgs/earthquakes/**/*.parquet')

Con vistas, el fichero .duckdb solo funciona en la máquina donde se construyó.
Al copiarlo a CI o a un servidor, cualquier consulta que tocara silver fallaba
con "No files found that match the pattern". Y como el warehouse se distribuye
—como asset de release y por R2— eso rompía la estrategia entera.

Con tablas, el .duckdb es autocontenido: se copia a cualquier sitio y funciona.
El coste es disco; el beneficio es que el artefacto sea realmente portable.

La frontera silver/gold importa: si una decisión es discutible ("¿qué hago
cuando hay dato observado y pronóstico para la misma hora?"), va en gold, donde
es visible y se puede cambiar. Silver debe ser aburrido.
"""
