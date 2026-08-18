"""Capa de transformación: bronze → silver → gold.

Los modelos son ficheros .sql numerados, uno por modelo, ejecutados en orden.
Es dbt sin dbt: misma disciplina (un modelo por fichero, dependencias
explícitas por orden, todo reconstruible desde cero) sin arrastrar 100 MB de
dependencias. Migrar a dbt después es mover los ficheros y añadir `ref()`.

Contrato de las tres capas:

  bronze — crudo, append-only, con duplicados. Nunca se toca.
  silver — limpio y deduplicado. NADA de lógica de negocio.
  gold   — agregados y features. Aquí sí van las decisiones analíticas.

La frontera silver/gold importa: si una decisión es discutible ("¿qué hago
cuando hay dato observado y pronóstico para la misma hora?"), va en gold, donde
es visible y se puede cambiar. Silver debe ser aburrido.
"""
