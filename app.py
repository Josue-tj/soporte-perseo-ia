import os
import time
import base64
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Perseo IA - Soporte Conversacional",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

GEMINI_CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Outfit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', 'Google Sans', sans-serif;
    }

    /* Fondo general estilo Gemini Dark Mode */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Mantiene transparente el encabezado y visible el botón de reabrir menú */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    [data-testid="collapsedControl"] {
        color: #e3e3e3 !important;
    }
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar Estilo Gemini Dark */
    section[data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Saludo Gemini Style Header */
    .gemini-header-title {
        background: linear-gradient(135deg, #4285f4 0%, #9b51e0 50%, #d946ef 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.8px;
        margin-bottom: 0px;
    }

    .gemini-subtext {
        color: #8e918f;
        font-size: 1.1rem;
        margin-top: 4px;
        margin-bottom: 25px;
    }

    /* Tarjetas de sugerencia estilo Gemini Chips */
    .suggestion-card {
        background: #1e1f20;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 16px 20px;
        cursor: pointer;
        transition: all 0.25s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .suggestion-card:hover {
        background: #28292a;
        border-color: #4285f4;
        transform: translateY(-2px);
    }

    .suggestion-icon {
        font-size: 1.4rem;
        margin-bottom: 10px;
    }

    .suggestion-text {
        font-size: 0.9rem;
        color: #c4c7c5;
        font-weight: 500;
    }

    /* Mensajes del Chat Estilo Gemini */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 1rem 0rem !important;
    }

    /* Estilo para mensaje del Asistente Gemini */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: transparent !important;
    }

    /* Avatar e íconos */
    .gemini-sparkle-icon {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #4285f4, #a855f7);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        box-shadow: 0 0 12px rgba(66, 133, 244, 0.4);
    }

    /* Caja de Input de Chat flotante */
    .stChatInputContainer {
        border-radius: 28px !important;
        background-color: #1e1f20 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 4px 10px !important;
    }

    .stChatInputContainer:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 15px rgba(168, 85, 247, 0.2) !important;
    }

    /* Badge de Estado */
    .gemini-badge {
        background: rgba(66, 133, 244, 0.15);
        color: #8ab4f8;
        border: 1px solid rgba(66, 133, 244, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
</style>
"""
st.markdown(GEMINI_CUSTOM_CSS, unsafe_allow_html=True)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

SYSTEM_PROMPT = """
Eres 'Perseo AI Assistant', un Asistente Senior de Soporte Técnico con inteligencia de estilo Google Gemini, especializado en el ERP y Sistema de Facturación 'Perseo PC' (Ecuador).

Tu tono debe ser profesional, servicial, amigable, claro y directo.
Al responder sobre un problema de Perseo PC, entrega respuestas estructuradas usando Markdown impecable:

1. 📍 **Diagnóstico Breve:** Identifica el módulo afectado y la causa técnica del error.
2. 🛠️ **Pasos para la Solución:** Lista clara numerada con la solución puntual en Perseo PC o Windows.
3. 💡 **Tip de Prevención / SRI:** Consejo rápido para evitar reincidencia o detalle sobre normativa del SRI Ecuador si aplica.

Si la consulta es continua (siguiente pregunta en la conversación), responde manteniendo el contexto previo de forma natural.
"""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

PREFERRED_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

def generate_gemini_response(contents):
    """
    Intenta generar contenido probando secuencialmente modelos activos.
    Evita errores 404 por modelos descontinuados.
    """
    if not api_key:
        raise ValueError("No se ha configurado la clave API GEMINI_API_KEY en el archivo .env")

    genai.configure(api_key=api_key)
    last_error = None

    # 1. Probar modelos recomendados activos
    for model_name in PREFERRED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            last_error = e
            continue

    # 2. Si fallan los preferidos, consultar modelos disponibles en la API
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in available:
            clean_name = m.replace("models/", "")
            if clean_name not in PREFERRED_MODELS:
                try:
                    model = genai.GenerativeModel(clean_name)
                    response = model.generate_content(contents)
                    return response.text, clean_name
                except Exception as e:
                    last_error = e
                    continue
    except Exception:
        pass

    raise last_error if last_error else RuntimeError("No se pudo conectar con ningún modelo activo de Gemini.")

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0;">
        <div class="gemini-sparkle-icon">✨</div>
        <div>
            <h3 style="margin:0; font-size: 1.1rem; color: #e3e3e3;">Perseo AI Chat</h3>
            <span style="font-size: 0.75rem; color: #8e918f;">Soporte Técnico Especializado</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    if api_key:
        st.markdown('<div class="gemini-badge">🟢 Gemini AI Conectado</div>', unsafe_allow_html=True)
    else:
        st.error("🔴 Clave API no configurada en .env")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📷 Adjuntar Captura de Pantalla")
    attached_image = st.file_uploader(
        "Sube una imagen del error en Perseo PC:",
        type=["jpg", "png", "jpeg"],
        help="El Asistente Gemini la analizará junto con tu mensaje"
    )

    image_preview = None
    if attached_image:
        image_preview = Image.open(attached_image)
        st.image(image_preview, caption="Imagen Adjunta para la consulta", use_container_width=True)

    st.divider()

    st.markdown("### 🌐 Servicios SRI Ecuador")
    st.caption("• WebService Recepción: **En línea**")
    st.caption("• WebService Autorización: **En línea**")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Limpiar Conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

st.markdown("""
<div style="padding-top: 10px;">
    <h1 class="gemini-header-title">Hola, Soporte Perseo</h1>
    <p class="gemini-subtext">¿Con qué problema o código de error te puedo ayudar hoy?</p>
</div>
""", unsafe_allow_html=True)

# Muestra las tarjetas de sugerencia solo si el chat está vacío
if len(st.session_state.messages) == 0:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔑 Error Firma Caducada\n\n'La firma electrónica se encuentra revocada o expirada al autorizar'", key="chip1", use_container_width=True):
            st.session_state.pending_prompt = "El cliente reporta: Error al firmar la factura, indica 'La firma electrónica se encuentra caducada o expirada'."
            st.rerun()

    with col2:
        if st.button("🌐 WebService SRI 500\n\n'Error 500 de comunicación con los servidores de comprobantes del SRI'", key="chip2", use_container_width=True):
            st.session_state.pending_prompt = "Tengo un problema al enviar retención: 'Error 500 de comunicación con la base de datos o WebService del SRI'."
            st.rerun()

    with col3:
        if st.button("📊 Falta Cuenta Contable\n\n'Error al contabilizar: No existe cuenta configurada para el grupo'", key="chip3", use_container_width=True):
            st.session_state.pending_prompt = "Al intentar guardar la venta sale el error: 'Falta asignar cuenta contable para el grupo de producto SERVICIOS'."
            st.rerun()

    with col4:
        if st.button("🔢 Secuencia Duplicada\n\n'Error de clave de acceso o número de comprobante duplicado'", key="chip4", use_container_width=True):
            st.session_state.pending_prompt = "El sistema muestra: 'Error de clave de acceso o secuencia de comprobante duplicada 001-002-00001234'."
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

# Renderizar historial de mensajes en pantalla
for msg in st.session_state.messages:
    avatar = "✨" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])

# Capturar nuevo prompt del usuario (desde input o chip de sugerencia)
user_prompt = st.chat_input("Escribe tu consulta sobre Perseo PC o describe el error...")

if st.session_state.pending_prompt and not user_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    # 1. Agregar mensaje del usuario a session state
    user_msg_data = {"role": "user", "content": user_prompt}
    if image_preview is not None:
        user_msg_data["image"] = image_preview

    st.session_state.messages.append(user_msg_data)

    # Renderizar el mensaje recién enviado
    with st.chat_message("user", avatar="👤"):
        if image_preview is not None:
            st.image(image_preview, width=300)
        st.markdown(user_prompt)

    # 2. Generar respuesta con Gemini AI usando motor fallback
    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Pensando y analizando caso en Perseo PC...)*")

        try:
            # Construir conversación completa para Gemini
            contents = [SYSTEM_PROMPT]
            
            # Incorporar el historial previo
            for past_msg in st.session_state.messages:
                role_label = "Usuario: " if past_msg["role"] == "user" else "Asistente Perseo: "
                contents.append(f"{role_label}{past_msg['content']}")

            # Adjuntar imagen si existe en la última interacción
            if image_preview is not None:
                contents.append(image_preview)

            response_text, model_used = generate_gemini_response(contents)

            # Renderizar respuesta formateada
            message_placeholder.markdown(response_text)

            # Guardar respuesta en historial
            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            message_placeholder.error(f"❌ Error de comunicación con Gemini AI: {e}")
