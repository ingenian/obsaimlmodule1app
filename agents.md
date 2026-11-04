# =====================================================================
#  EL DETECTIVE DE COMERCIOS
#  Lee un archivo de compras, descubre que "OXXO4521" y "OXXO 4521"
#  son la misma tienda, quita las compras repetidas y te devuelve
#  un archivo ordenado. Antes de cambiar nada, te pide permiso.
# =====================================================================
import base64      # para convertir el archivo en un enlace de descarga
import hmac        # para comparar contraseñas de forma segura
import json        # para leer las respuestas del modelo (JSON)
import os          # para leer variables de entorno
import unicodedata # para quitar acentos
from pathlib import Path

import pandas as pd        # para trabajar con tablas
import streamlit as st     # para hacer la página web


# ---------------------------------------------------------------------
# PASO 0. Las llaves secretas (nunca se escriben en el código)
# ---------------------------------------------------------------------
def leer_secreto(nombre, si_no_existe=""):
    """Busca la llave en los secretos de Streamlit; si no está, en el sistema."""
    try:
        if nombre in st.secrets:
            return str(st.secrets[nombre])
    except Exception:
        pass
    return os.getenv(nombre, si_no_existe)


LLAVE_GEMINI = leer_secreto("GEMINI_API_KEY")
MODELO = leer_secreto("GEMINI_MODELO", "gemini-3.5-flash-lite")
CLAVE_ACCESO = leer_secreto("CLAVE_ACCESO")

st.set_page_config(page_title="Detective de comercios", page_icon="🕵️")
st.title("🕵️ Detective de comercios")

# La puerta: si la app tiene contraseña, la pide una vez por sesión.
if CLAVE_ACCESO and not st.session_state.get("puede_entrar"):
    clave = st.text_input("Contraseña", type="password")
    if not clave or not hmac.compare_digest(clave.encode(), CLAVE_ACCESO.encode()):
        if clave:
            st.error("Contraseña incorrecta.")
        st.stop()
    st.session_state.puede_entrar = True

# Las instrucciones del detective viven en agents.md (como su libreta de reglas).
libreta = next((p for p in Path(__file__).parent.iterdir() if p.name.lower() == "agents.md"), None)
if libreta is None:
    st.error("Falta el archivo agents.md junto a app.py.")
    st.stop()
INSTRUCCIONES = libreta.read_text(encoding="utf-8")


# ---------------------------------------------------------------------
# PASO 1. Pedir el archivo
# ---------------------------------------------------------------------
archivo = st.file_uploader("Sube tu archivo de compras (CSV o Excel)", type=["csv", "xlsx"])
if archivo is None:
    st.info("Sube un archivo para empezar. Al modelo solo le enseño los nombres de los "
            "comercios, nunca los montos ni las fechas.")
    st.stop()


# ---------------------------------------------------------------------
# PASO 2. Leer el archivo y encontrar las columnas
# ---------------------------------------------------------------------
if archivo.name.endswith(".xlsx"):
    tabla = pd.read_excel(archivo, dtype=str).fillna("")
else:
    tabla = pd.read_csv(archivo, dtype=str, keep_default_na=False)


def buscar_columna(pistas):
    """Devuelve la primera columna cuyo nombre contenga alguna pista."""
    for columna in tabla.columns:
        for pista in pistas:
            if pista in columna.lower():
                return columna
    return None


col_comercio = buscar_columna(["comercio", "merchant", "nombre"])
col_fecha = buscar_columna(["fecha", "date"])
col_hora = buscar_columna(["hora", "time"])
col_monto = buscar_columna(["monto", "importe", "amount"])

if not (col_comercio and col_fecha and col_monto):
    st.error(f"No encontré las columnas de comercio, fecha y monto. Columnas del archivo: {list(tabla.columns)}")
    st.stop()

# Juntamos fecha y hora, y convertimos el monto en número.
fecha_y_hora = tabla[col_fecha] + " " + (tabla[col_hora] if col_hora and col_hora != col_fecha else "")
tabla["_cuando"] = pd.to_datetime(fecha_y_hora, errors="coerce", dayfirst=True, format="mixed")
tabla["_monto"] = pd.to_numeric(tabla[col_monto].str.replace(",", ""), errors="coerce")
tabla["comercio_original"] = tabla[col_comercio].str.strip()


# ---------------------------------------------------------------------
# PASO 3. Preguntarle al modelo quién es cada comercio
# ---------------------------------------------------------------------
def limpiar_sin_ia(nombre):
    """Plan B, sin modelo: mayúsculas, sin acentos y sin espacios de más."""
    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c))
    limpio = " ".join(sin_acentos.upper().split())
    return {"original": nombre, "comercio": limpio, "sucursal": "", "agregador": "",
            "motivo": "Limpieza básica, sin modelo"}


def preguntar_al_modelo(nombres):
    """Manda SOLO los nombres a Gemini y recibe una ficha (diccionario) por nombre."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=LLAVE_GEMINI)
    pistas, fichas = [], []
    for inicio in range(0, len(nombres), 150):          # de 150 en 150, para no gastar la cuota
        grupo = nombres[inicio:inicio + 150]
        respuesta = cliente.models.generate_content(
            model=MODELO,
            contents="Nombres de comercio:\n" + json.dumps(grupo, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES,       # las reglas de agents.md
                response_mime_type="application/json",  # que conteste en JSON
                temperature=0,                          # que conteste siempre igual
            ),
        )
        datos = json.loads(respuesta.text)
        pistas += datos.get("hallazgos", [])
        fichas += datos.get("comercios", [])
    return pistas, fichas


# Solo preguntamos una vez por archivo (st.session_state es la memoria de la página).
if st.session_state.get("archivo_visto") != archivo.name + str(archivo.size):
    nombres = sorted(set(tabla["comercio_original"]))     # cada nombre una sola vez
    pistas, fichas, quien = [], [], "limpieza básica"
    if LLAVE_GEMINI:
        try:
            with st.spinner("El detective está pensando…"):
                pistas, fichas = preguntar_al_modelo(nombres)
            quien = f"Gemini ({MODELO})"
        except Exception as error:
            pistas = [f"No pude hablar con Gemini ({type(error).__name__}). Si es 429, espera un minuto."]
    else:
        pistas = ["No hay GEMINI_API_KEY: solo hice limpieza básica."]
    # Revisamos que el modelo no se haya saltado ningún nombre.
    respondidos = {ficha.get("original") for ficha in fichas}
    for nombre in nombres:
        if nombre not in respondidos:
            fichas.append(limpiar_sin_ia(nombre))
    st.session_state.archivo_visto = archivo.name + str(archivo.size)
    st.session_state.fichas = fichas
    st.session_state.pistas = pistas
    st.session_state.quien = quien
    st.session_state.respuesta = None

mapa = pd.DataFrame(st.session_state.fichas).reindex(
    columns=["original", "comercio", "sucursal", "agregador", "motivo"]).fillna("").astype(str)
mapa = mapa.rename(columns={"original": "comercio_original", "comercio": "comercio_normalizado"})


# ---------------------------------------------------------------------
# PASO 4. Mostrar lo que encontró y dejar que la persona lo corrija
# ---------------------------------------------------------------------
st.subheader("Lo que encontró el detective")
mapa_corregido = st.data_editor(mapa, hide_index=True, disabled=["comercio_original"])


# ---------------------------------------------------------------------
# PASO 5. Buscar compras repetidas
#   Mismo comercio + misma sucursal + mismo monto, con menos de 2 minutos
#   de diferencia = la misma compra anotada dos veces.
# ---------------------------------------------------------------------
todo = tabla.merge(mapa_corregido, on="comercio_original", how="left")
todo = todo.sort_values("_cuando")                       # ordenamos por fecha y hora
todo["repetida"] = False
primera_vez = {}                                         # llave -> cuándo la vimos primero
for fila, compra in todo.iterrows():
    if pd.isna(compra["_cuando"]):
        continue
    llave = (compra["comercio_normalizado"], compra["sucursal"], compra["_monto"])
    if llave in primera_vez and compra["_cuando"] - primera_vez[llave] <= pd.Timedelta(minutes=2):
        todo.at[fila, "repetida"] = True                 # ya la habíamos visto: es repetida
    else:
        primera_vez[llave] = compra["_cuando"]           # es nueva: la anotamos
todo = todo.sort_index()

repetidas = int(todo["repetida"].sum())
st.markdown(
    f"- Revisé **{len(todo)} compras** con **{st.session_state.quien}**.\n"
    f"- **{mapa['comercio_original'].nunique()} nombres** son en realidad "
    f"**{mapa_corregido['comercio_normalizado'].nunique()} comercios**.\n"
    f"- Encontré **{repetidas} compras repetidas**."
)
for pista in st.session_state.pistas:
    st.markdown(f"  - 🔎 {pista}")


# ---------------------------------------------------------------------
# PASO 6. Pedir permiso y entregar el archivo corregido
# ---------------------------------------------------------------------
st.markdown("**¿Estás de acuerdo con lo que encontré?**")
si, no = st.columns(2)
if si.button("✅ Sí", type="primary"):
    st.session_state.respuesta = "si"
if no.button("✏️ No, quiero corregir"):
    st.session_state.respuesta = "no"

if st.session_state.respuesta == "no":
    st.info("Corrige la tabla de arriba y luego pulsa **Sí**.")

if st.session_state.respuesta == "si":
    final = todo[~todo["repetida"]].drop(columns=["repetida", "_cuando", "_monto"])
    csv = final.to_csv(index=False).encode("utf-8-sig")
    st.success(f"Listo: {len(final)} compras, sin repetidas. El nombre original se conserva.")
    enlace = base64.b64encode(csv).decode()
    st.markdown(f'<a href="data:text/csv;base64,{enlace}" download="compras_corregidas.csv">'
                "⬇️ Descargar archivo corregido</a>", unsafe_allow_html=True)
    st.download_button("Descargar (otra forma)", csv, "compras_corregidas.csv", "text/csv")
