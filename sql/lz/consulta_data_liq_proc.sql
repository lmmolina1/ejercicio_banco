SELECT
    t1.id_epica,
    t1.periodo,
    t2.cod_proc AS codigo_proceso,
    t2.procedimiento,
    t2.actividad
FROM (
SELECT DISTINCT 
        ig.id_epica, 
        pb.codigo_proceso, 
        ig.periodo
    FROM resultados_vspc_dise.cdeproc_sabana_procesos_beneficios pb
    JOIN resultados_vspc_dise.cdeproc_sabana_informacion_general ig
        ON ig.id_epica = pb.id_epica
    WHERE ig.periodo = '2026Q1'
) t1
JOIN (
    SELECT 
        cod_proc,
        procedimiento,
        actividad
    FROM resultados_serv_para_los_clientes.bpms_data_liquida
    WHERE cod_proc IS NOT NULL
      AND tipo_actividad IN ('TAREA', 'CONTROL', 'CONTROL PARCIAL', 'PROCEDIMIENTO')
      AND cod_proc NOT LIKE '%CM%'
    GROUP BY 
        cod_proc,
        procedimiento,
        actividad
) t2
ON t1.codigo_proceso = t2.cod_proc