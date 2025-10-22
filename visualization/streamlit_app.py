import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="Dashboard Supabase", layout="wide")
st.title("📊 Dashboard Supabase (readonly)")

# ---- Helper de conexión y caché ----
@st.cache_data(ttl=600)
def run_sql(sql: str, params=None) -> pd.DataFrame:
    cfg = st.secrets["postgres"]
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode=cfg.get("sslmode", "require"),
        cursor_factory=RealDictCursor
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params or {})
            rows = cur.fetchall()
            return pd.DataFrame(rows)
    finally:
        conn.close()

# ---- Parámetros (tabla fija) ----
TABLA = "public.summary"

# ---- Opciones de filtro (traídas desde la BD) ----
df_emps = run_sql(f"SELECT DISTINCT employee_name FROM {TABLA} ORDER BY 1;")
df_stats = run_sql(f"SELECT DISTINCT status FROM {TABLA} ORDER BY 1;")

empleados = ["(Todos)"] + (df_emps["employee_name"].dropna().tolist() if not df_emps.empty else [])
estados   = ["(Todos)"] + (df_stats["status"].dropna().tolist() if not df_stats.empty else [])

with st.sidebar:
    st.header("Filtros")
    empleado_sel = st.selectbox("Empleado", options=empleados, index=0)
    estado_sel   = st.selectbox("Estado", options=estados, index=0)
    busqueda     = st.text_input("Buscar texto (título/observación)", value="")

# ---- Construcción dinámica del WHERE seguro ----
where = []
params = {}
if empleado_sel and empleado_sel != "(Todos)":
    where.append("employee_name = %(emp)s")
    params["emp"] = empleado_sel

if estado_sel and estado_sel != "(Todos)":
    where.append("status = %(st)s")
    params["st"] = estado_sel

if busqueda:
    where.append("(task_title ILIKE %(q)s OR observation ILIKE %(q)s)")
    params["q"] = f"%{busqueda}%"

where_clause = ("WHERE " + " AND ".join(where)) if where else ""

# ---- Consulta principal (datos crudos) ----
sql_data = f"""
    SELECT
        employee_name,
        task_title,
        status,
        observation
    FROM {TABLA}
    {where_clause}
    ORDER BY employee_name, task_title;
"""
df = run_sql(sql_data, params)

# ---- Agregados para gráficos ----
sql_by_status = f"""
    SELECT status, COUNT(*) AS n
    FROM {TABLA}
    {where_clause}
    GROUP BY 1
    ORDER BY 2 DESC;
"""
df_by_status = run_sql(sql_by_status, params)

sql_by_emp = f"""
    SELECT employee_name, COUNT(*) AS n
    FROM {TABLA}
    {where_clause}
    GROUP BY 1
    ORDER BY 2 DESC;
"""
df_by_emp = run_sql(sql_by_emp, params)

# ---- Métricas ----
col_m1, col_m2, col_m3 = st.columns(3)
total = len(df) if not df.empty else 0
n_completado = int(df[df["status"].str.lower() == "completado"].shape[0]) if not df.empty and "status" in df else 0
n_pendiente  = int(df[df["status"].str.lower() == "pendiente"].shape[0]) if not df.empty and "status" in df else 0

col_m1.metric("Total de tareas", total)
col_m2.metric("Completadas", n_completado)
col_m3.metric("Pendientes", n_pendiente)

st.divider()

# ---- Gráficos ----
c1, c2 = st.columns(2)

with c1:
    st.subheader("Tareas por estado")
    if not df_by_status.empty:
        st.bar_chart(df_by_status.set_index("status")["n"])
    else:
        st.info("Sin datos para graficar por estado.")

with c2:
    st.subheader("Tareas por empleado")
    if not df_by_emp.empty:
        st.bar_chart(df_by_emp.set_index("employee_name")["n"])
    else:
        st.info("Sin datos para graficar por empleado.")

st.divider()

# ---- Tabla ----
st.subheader("Detalle de tareas")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar CSV", data=csv, file_name="summary_filtrado.csv", mime="text/csv")
else:
    st.info("No se encontraron registros con los filtros actuales.")
