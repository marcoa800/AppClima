-- Observaciones de aves limpias y deduplicadas.
--
-- Grano: (checklist_id, species_code, location_id).
--
-- El checklist (subId en eBird) identifica una salida de campo concreta de un
-- observador. Una especie aparece una sola vez por checklist, así que la pareja
-- (checklist, especie) es la clave natural. Incluimos location_id porque el
-- mismo checklist puede caer dentro del radio de dos ciudades ancla cercanas
-- (Madrid y Barcelona no, pero es una propiedad general que conviene respetar).
--
-- Filtramos `obs_valid` porque eBird marca así los registros que su comité de
-- revisión rechazó: identificaciones erróneas, escapes de cautividad, o
-- rarezas sin documentar. Incluirlos añadiría especies fantasma al análisis.
--
-- Ojo con este dataset: es ciencia ciudadana. El número de observaciones
-- depende de cuánta gente salió a mirar, no solo de cuántas aves había. Ver el
-- aviso en schemas/birds.py antes de sacar conclusiones sobre migración.

CREATE OR REPLACE VIEW silver_bird_observations AS
WITH ranked AS (
    SELECT
        location_id,
        search_radius_km,
        species_code,
        common_name,
        scientific_name,
        obs_datetime,
        obs_date_only,
        how_many,
        lat,
        lon,
        loc_id,
        loc_name,
        obs_valid,
        obs_reviewed,
        checklist_id,
        _ingested_at,
        row_number() OVER (
            PARTITION BY checklist_id, species_code, location_id
            ORDER BY _ingested_at DESC
        ) AS _rn
    FROM {{bronze_birds}}
    WHERE obs_valid
)
SELECT * EXCLUDE (_rn)
FROM ranked
WHERE _rn = 1;
