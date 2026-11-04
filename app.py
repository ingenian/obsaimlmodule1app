"""Conciliador de comercios

1. Pide el archivo de transacciones.
2. Lo lee y el agente (Gemini + agents.md) encuentra los patrones en los nombres de comercio.
3. Muestra los hallazgos y pregunta si estás de acuerdo.
4. Devuelve el archivo modificado.
"""
import io
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st


# ------------------------------------------------------------------ secretos y configuración
def leer_secreto(nombre: str, por_defecto: str = "") -> str:
    """Lee primero los secretos de Streamlit Cloud y después las variables de entorno."""
    try:
        if nombre in st.secrets:
            return str(st.secrets[nombre])
    except Exception:  # no hay archivo de secretos (por ejemplo, en local)
        pass
    return os.getenv(nombre, por_defecto)


GEMINI_API_KEY = leer_secreto("GEMINI_API_KEY")
GEMINI_MODELO = leer_secreto("GEMINI_MODELO", "gemini-3.5-flash-lite")
CLAVE_ACCESO = leer_secreto("CLAVE_ACCESO")  # opcional: protege la app publicada

INSTRUCCIONES_AGENTE = (Path(__file__).parent / "agents.md").read_text(encoding="utf-8")
LOTE_NOMBRES = 150  # nombres por llamada al modelo

st.set_page_config(page_title="Conciliador de comercios", page_icon="🧾")
st.title("🧾 Conciliador de comercios")

if CLAVE_ACCESO and st.session_state.get("acceso") != CLAVE_ACCESO:
    clave = st.text_input("Clave de acceso", type="password")
    if clave != CLAVE_ACCESO:
        st.stop()
    st.session_state.acceso = clave


# ------------------------------------------------------------------ lectura del archivo
def leer_archivo(archivo) -> pd.DataFrame:
    if archivo.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(archivo, dtype=str).fillna("")
    texto = archivo.getvalue().decode("utf-8-sig", errors="replace")
    separador = ";" if texto.count(";") > texto.count(",") else ","
    return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str, keep_default_na=False)


def adivinar_columna(columnas, pistas):
    for c in columnas:
        if any(p in c.lower() for p in pistas):
            return c
    return None


def a_fecha_hora(df: pd.DataFrame, col_fecha: str, col_hora: str | None) -> pd.Series:
    texto = df[col_fecha].astype(str)
    if col_hora:
        texto = texto + " " + df[col_hora].astype(str)
    iso = texto.str.match(r"^\s*\d{4}-\d{2}-\d{2}")
    fechas = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    fechas[iso] = pd.to_datetime(texto[iso], errors="coerce")
    fechas[~iso] = pd.to_datetime(texto[~iso], errors="coerce", dayfirst=True, format="mixed")
    return fechas


def a_monto(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce").round(2)


# ------------------------------------------------------------------ agente
def normalizar_con_agente(nombres: list[str]) -> dict:
    """Envía SOLO los nombres de comercio a Gemini, con agents.md como instrucciones."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=GEMINI_API_KEY)
    hallazgos, comercios = [], []
    for i in range(0, len(nombres), LOTE_NOMBRES):
        lote = nombres[i:i + LOTE_NOMBRES]
        respuesta = cliente.models.generate_content(
            model=GEMINI_MODELO,
            contents="Nombres de comercio:\n" + json.dumps(lote, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES_AGENTE,
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        datos = json.loads(respuesta.text)
        hallazgos += datos.get("hallazgos", [])
        comercios += datos.get("comercios", [])
    return {"hallazgos": hallazgos, "comercios": comercios}


def normalizar_basico(nombre: str) -> dict:
    """Respaldo sin IA: mayúsculas, sin acentos, número de sucursal separado."""
    texto = "".join(c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)).upper()
    texto = re.sub(r"([A-Z]{2,})(\d{3,6})\b", r"\1 \2", texto)
    texto = " ".join(re.sub(r"[^A-Z0-9 ]", " ", texto).split())
    m = re.search(r"\b(\d{3,6})\b", texto)
    comercio = texto[:m.start()].strip() if m and m.start() > 0 else texto
    return {"original": nombre, "comercio": comercio, "sucursal": m.group(1) if m and m.start() > 0 else "",
            "ubicacion": texto[m.end():].strip() if m and m.start() > 0 else "", "agregador": "",
            "motivo": "Limpieza básica sin IA"}


def construir_mapeo(nombres: list[str]) -> tuple[pd.DataFrame, list[str], str]:
    if GEMINI_API_KEY:
        try:
            r = normalizar_con_agente(nombres)
            mapeo = pd.DataFrame(r["comercios"])
            faltan = [n for n in nombres if n not in set(mapeo.get("original", []))]
            if faltan:  # el modelo omitió algún nombre: se completa con la limpieza básica
                mapeo = pd.concat([mapeo, pd.DataFrame([normalizar_basico(n) for n in faltan])])
            return mapeo, r["hallazgos"], f"Gemini ({GEMINI_MODELO})"
        except Exception as e:
            aviso = f"No pude usar Gemini ({type(e).__name__}). Si es un error 429, espera un minuto."
            return pd.DataFrame([normalizar_basico(n) for n in nombres]), [aviso], "limpieza básica"
    return (pd.DataFrame([normalizar_basico(n) for n in nombres]),
            ["Sin GEMINI_API_KEY: solo se aplicó limpieza básica."], "limpieza básica")


# ------------------------------------------------------------------ duplicados
NOMBRES_SALIDA = {"original": "comercio_original", "comercio": "comercio_normalizado",
                  "sucursal": "sucursal_normalizada", "ubicacion": "ubicacion", "agregador": "agregador",
                  "motivo": "motivo_agente"}


def marcar_duplicados(df: pd.DataFrame, minutos: float) -> pd.DataFrame:
    """Mismo comercio, sucursal y monto con menos de `minutos` de diferencia: se conserva la primera."""
    df = df.sort_values("_fecha_hora").copy()
    df["es_duplicado"] = False
    df["grupo_duplicado"] = ""
    n = 0
    claves = ["comercio_normalizado", "sucursal_normalizada", "_monto"]
    for _, grupo in df.dropna(subset=["_fecha_hora", "_monto"]).groupby(claves):
        primera = None
        for idx, fila in grupo.iterrows():
            if primera is not None and fila["_fecha_hora"] - primera["_fecha_hora"] <= pd.Timedelta(minutes=minutos):
                if not df.at[primera.name, "grupo_duplicado"]:
                    n += 1
                    df.at[primera.name, "grupo_duplicado"] = f"D{n:03d}"
                df.at[idx, "grupo_duplicado"] = df.at[primera.name, "grupo_duplicado"]
                df.at[idx, "es_duplicado"] = True
            else:
                primera = fila
    return df.sort_index()


# ------------------------------------------------------------------ interfaz
archivos = st.file_uploader("Sube tu archivo de transacciones (CSV o Excel)",
                            type=["csv", "xlsx", "xls"], accept_multiple_files=True)
if not archivos:
    st.info("Sube uno o varios archivos para empezar. Al modelo solo se le envían los nombres de "
            "comercio, nunca montos ni fechas.")
    st.stop()

datos = pd.concat([leer_archivo(a).assign(archivo_origen=a.name) for a in archivos], ignore_index=True)
columnas = [c for c in datos.columns if c != "archivo_origen"]

with st.expander("Columnas del archivo", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    col_comercio = c1.selectbox("Comercio", columnas,
                                index=columnas.index(adivinar_columna(columnas, ["comercio", "merchant", "nombre"]) or columnas[0]))
    col_fecha = c2.selectbox("Fecha", columnas,
                             index=columnas.index(adivinar_columna(columnas, ["fecha", "date"]) or columnas[0]))
    opciones_hora = ["(incluida en la fecha)"] + columnas
    sugerida_hora = adivinar_columna([c for c in columnas if c != col_fecha], ["hora", "time"])
    col_hora = c3.selectbox("Hora", opciones_hora,
                            index=opciones_hora.index(sugerida_hora) if sugerida_hora else 0)
    col_monto = c4.selectbox("Monto", columnas,
                             index=columnas.index(adivinar_columna(columnas, ["monto", "importe", "amount"]) or columnas[-1]))
    minutos = st.slider("Ventana para duplicados (minutos)", 0.5, 30.0, 2.0, 0.5)

clave_archivo = "|".join(a.name + str(a.size) for a in archivos) + col_comercio
if st.session_state.get("clave_archivo") != clave_archivo:
    nombres = sorted(datos[col_comercio].astype(str).str.strip().unique())
    with st.spinner("El agente está revisando los nombres de comercio…"):
        mapeo, hallazgos, motor = construir_mapeo(nombres)
    st.session_state.pop("tabla_mapeo", None)  # borra correcciones de un archivo anterior
    st.session_state.update(clave_archivo=clave_archivo, mapeo=mapeo, hallazgos=hallazgos,
                            motor=motor, respuesta=None)

mapeo = (st.session_state.mapeo.reindex(columns=list(NOMBRES_SALIDA)).fillna("")
         .astype(str).rename(columns=NOMBRES_SALIDA))
transacciones = datos.copy()
transacciones["comercio_original"] = transacciones[col_comercio].astype(str).str.strip()
transacciones["_fecha_hora"] = a_fecha_hora(datos, col_fecha, None if col_hora.startswith("(") else col_hora)
transacciones["_monto"] = a_monto(datos[col_monto])

# ---- hallazgos: el mensaje se escribe después de la tabla para contar con las correcciones
mensaje = st.chat_message("assistant").empty()
editado = st.data_editor(mapeo, hide_index=True, width="stretch", disabled=["comercio_original"], key="tabla_mapeo")
resultado = marcar_duplicados(transacciones.merge(editado, on="comercio_original", how="left"), minutos)
quitar = int(resultado["es_duplicado"].sum())
texto = (
    f"Revisé **{len(transacciones)} transacciones** de {len(archivos)} archivo(s) con **{st.session_state.motor}**.\n\n"
    f"- **{editado['comercio_original'].nunique()} nombres distintos** corresponden a "
    f"**{editado['comercio_normalizado'].nunique()} comercios** y "
    f"**{len(editado[['comercio_normalizado', 'sucursal_normalizada']].drop_duplicates())} sucursales**.\n"
    f"- **{quitar} transacciones duplicadas** (mismo comercio, sucursal y monto en menos de {minutos:g} minutos)."
)
if st.session_state.hallazgos:
    texto += "\n\n**Hallazgos:**\n" + "\n".join(f"- {h}" for h in st.session_state.hallazgos)
mal_fecha = int(transacciones["_fecha_hora"].isna().sum())
if mal_fecha:
    texto += f"\n\n⚠️ {mal_fecha} fecha(s) no se pudieron leer; esas filas no se revisan como duplicado."
texto += "\n\nPuedes corregir los nombres en la tabla de abajo. **¿Estás de acuerdo con los hallazgos?**"
mensaje.markdown(texto)

duplicados = resultado[resultado["grupo_duplicado"] != ""]
if len(duplicados):
    with st.expander(f"Ver duplicados ({quitar} se quitarán)"):
        st.dataframe(duplicados[["grupo_duplicado", "es_duplicado", "archivo_origen", "comercio_original",
                                 "comercio_normalizado", "sucursal_normalizada", "_fecha_hora", "_monto"]]
                     .sort_values(["grupo_duplicado", "_fecha_hora"]), hide_index=True, width="stretch")

c1, c2 = st.columns(2)
if c1.button("✅ Sí, estoy de acuerdo", type="primary", width="stretch"):
    st.session_state.respuesta = "si"
if c2.button("✏️ No, quiero corregir", width="stretch"):
    st.session_state.respuesta = "no"

if st.session_state.respuesta == "no":
    st.info("Corrige el comercio, la sucursal o el agregador en la tabla y después pulsa **Sí, estoy de acuerdo**.")

if st.session_state.respuesta == "si":
    salida = resultado[~resultado["es_duplicado"]].drop(columns=["es_duplicado", "_fecha_hora", "_monto"])
    with st.chat_message("assistant"):
        st.markdown(f"Listo: el archivo modificado tiene **{len(salida)} transacciones**. Conserva todas las "
                    "columnas originales y agrega el comercio normalizado, la sucursal y el agregador. "
                    f"Quité {quitar} duplicado(s).")
        st.download_button("⬇️ Descargar archivo modificado (CSV)",
                           salida.to_csv(index=False).encode("utf-8-sig"),
                           "transacciones_conciliadas.csv", "text/csv", type="primary")
