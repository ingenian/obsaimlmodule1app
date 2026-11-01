# AGENTS.md · [Nombre de la app]

> Este fichero lo leen los agentes de programación (Copilot, Cursor, Codex, Gemini CLI y otros) antes de tocar vuestro código. Para Claude Code, cread un `CLAUDE.md` con una sola línea: `Sigue las instrucciones de AGENTS.md`. Para Gemini CLI, haced lo mismo con `GEMINI.md`.

## Qué es este proyecto

"Asistente de reconciliacion de invariantes que  a partir de la captura de distinto con el mismo layout, normaliza, correlaciona, detecta invariantes, clasifica,  y genera un solo archivo con la conciliacion resuelta".

## Cómo está hecho

- Python 3.12.
- Interfaz: [Streamlit (https://hola-ia-xceaccbpbnlolrahh5yj3a.streamlit.app/) ].
- IA: API de Gemini con el SDK `google-genai`. El modelo está en la constante `MODELO` de `app.py`.
- Archivos: `app.py` (toda la app), `requirements.txt` (dependencias) y `README.md`.
- La especificación completa está en [enlace a vuestra especificación].

## Reglas

- La clave de la API va SIEMPRE en secretos (`st.secrets` en la ruta A, variable de entorno `GEMINI_API_KEY` en la ruta B). Nunca en el código, en el README ni en el chat.
- Cada llamada a la API va dentro de `try/except` y muestra un mensaje claro para el usuario.
- Textos de la interfaz en español, sencillos, pensados para alguien sin conocimientos técnicos.
- Cambios pequeños: uno por petición. Al terminar, explica qué has cambiado y por qué.
- Si añades una librería, añádela también a `requirements.txt` y dilo.
- No uses datos personales reales. Para probar, inventa ejemplos.

## Cómo comprobar que funciona

- Ruta A: `streamlit run app.py` en local (con `.streamlit/secrets.toml`), o haz push y revisa la app en Streamlit Cloud.
- Ruta B: `python app.py` con `GEMINI_API_KEY` exportada, o sube los archivos al Space.
- Casos de prueba (entrada → lo que esperamos):
  1. [entrada] → [respuesta esperada]
  2. [entrada] → [respuesta esperada]
  3. [entrada fuera de tema] → [la app dice amablemente que no puede ayudar con eso]

## Qué no hacer

- No borres ni reescribas el README sin preguntar.
- No cambies el modelo ni la arquitectura sin preguntar.
- No hagas push ni despliegues sin que yo lo haya revisado.
