-- Macros reutilizables.

-- Distancia sobre la superficie terrestre, en kilómetros.
--
-- Se usa para dos cosas: asociar sismos a ciudades cercanas, y detectar
-- réplicas alrededor de un sismo principal. La alternativa sería la extensión
-- spatial de DuckDB, pero para distancia punto-a-punto es una dependencia
-- innecesaria: la fórmula cabe en seis líneas.
--
-- 6371.0088 km es el radio medio de la Tierra (IUGG). Con la Tierra tratada
-- como esfera el error es de hasta ~0,3%, irrelevante para agrupar sismos.
CREATE OR REPLACE MACRO haversine_km(lat1, lon1, lat2, lon2) AS
    6371.0088 * 2 * asin(sqrt(
        pow(sin(radians(lat2 - lat1) / 2), 2)
        + cos(radians(lat1)) * cos(radians(lat2))
          * pow(sin(radians(lon2 - lon1) / 2), 2)
    ));

-- Distancia circular entre dos días del año, tratando el 31 de diciembre y el
-- 1 de enero como vecinos. Sin esto, la climatología del 1 de enero se
-- calcularía solo con datos de enero, ignorando la última semana de diciembre.
CREATE OR REPLACE MACRO doy_distance(doy_a, doy_b) AS
    least(abs(doy_a - doy_b), 366 - abs(doy_a - doy_b));
