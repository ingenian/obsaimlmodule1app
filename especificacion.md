# Especificación · "Agente re-conciliacion de invariantes"

Agente de AI con enfoque financiero contable particularmente enfocado en la conciliacion de diferentes archivos de movimientos transaccionales provenientes de canales de comercio fisicos y/o comercio electronio donde 

## 1. Problema y usuario

- **Quién tiene el problema:** Area de Conciliacion Financiera
- **Cómo lo resuelve hoy:** Proceso Manual
- **Qué le molesta de cómo lo hace hoy:**  No se termina en tiempo y forma el cierre contable
- **Qué parte resuelve la IA:** Comparar, encontrar diferencias, generar un archivo final y hacerlo en tiempo
## 2. Qué hace el producto

Máximo tres funcionalidades. Si hay más, van al apartado 8.

1. [Funcionalidad 1] 
2. [Funcionalidad 2]
3. [Funcionalidad 3]

## 3. Entradas y salidas

| El usuario da… | La app devuelve… | Ejemplo |
|---|---|---|
| [un texto, una pregunta, un archivo CSV…] | [un resumen, una respuesta, una categoría…] | [ejemplo concreto] |

El agente recibe de diferentes fuentes un archivo con el mismo layout, contenido similar pero con diferencia en la trazabilidad de los movimientos contables, el agente debera comparar y generar un solo archivo correcto



## 4. La pieza de IA

- **Opción elegida:** [API de un LLM (Gemini) · modelo de Hugging Face · RAG sobre nuestros documentos]
- **Por qué:** [qué gana la app con esa opción]
- **Instrucciones para el modelo (system prompt):** [cómo debe comportarse, tono, qué no debe hacer]

## 5. Flujo del usuario

1. [El usuario entra y ve…]
2. [Escribe o sube…]
3. [Recibe…]

## 6. Restricciones

- Coste cero: capa gratuita de la API y despliegue gratuito (ruta A o B).
- La clave de la API va en secretos, nunca en el código.
- Sin datos personales reales.
- Lenguaje sencillo, para alguien sin conocimientos técnicos.
- [Otras restricciones de vuestro problema]

## 7. Criterios de aceptación

La app está bien si:

| Entrada | Resultado esperado |
|---|---|
| [caso normal] | [qué debe pasar] |
| [caso límite: texto vacío, pregunta fuera de tema…] | [qué debe pasar] |
| [error: se acaba la cuota] | [mensaje claro para el usuario] |

## 8. Fuera de alcance (por ahora)

- [Ideas que dejáis para después]

## 9. Despliegue

- **Ruta:** [A (Streamlit Community Cloud) · B (Hugging Face Spaces)]
- **Si trabajáis en equipo (opcional):** [qué app o funcionalidad construye cada persona]
