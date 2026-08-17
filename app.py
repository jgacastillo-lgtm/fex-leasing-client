import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy_financial as npf
import json
import os

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="FEX Capital - Portal de Clientes", layout="centered")

LOGO_PATH = "LOGO_FEX.png"

# REEMPLAZA ESTA LIGA CON LA URL REAL DE TU GOOGLE SHEETS
HOJA_DATOS_URL = "URL_DE_TU_GOOGLE_SHEETS_AQUI"

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource(ttl=60)
def cargar_base_datos():
    # Leer el secreto que guardamos en Streamlit
    creds = json.loads(st.secrets["gcp_service_account_json"])
    # Establecer conexión
    conn = st.connection("gsheets", type=GSheetsConnection, service_account_info=creds)
    # Descargar la tabla de clientes
    df = conn.read(spreadsheet=HOJA_DATOS_URL)
    return df

# ==========================================
# 3. GESTIÓN DE SESIÓN (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.datos_cliente = None

# ==========================================
# 4. PANTALLA DE ACCESO
# ==========================================
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; color: #1B1B1B;'>Portal de Arrendamiento</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        password_input = st.text_input("Código de Acceso", type="password", placeholder="Ingresa tu clave corporativa")
        
        if st.button("Ingresar al Cotizador", use_container_width=True):
            if password_input:
                try:
                    df_clientes = cargar_base_datos()
                    # Buscar si el password existe en la columna 'Password'
                    cliente_match = df_clientes[df_clientes['Password'] == password_input]
                    
                    if not cliente_match.empty:
                        # Guardar los datos del cliente en la sesión
                        st.session_state.datos_cliente = cliente_match.iloc[0].to_dict()
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("Código de acceso incorrecto. Verifica con tu ejecutivo de FEX Capital.")
                except Exception as e:
                    st.error("Error de conexión. Por favor, intenta más tarde.")
            else:
                st.warning("Por favor, ingresa un código válido.")

# ==========================================
# 5. PANTALLA DEL COTIZADOR VIP
# ==========================================
else:
    cliente = st.session_state.datos_cliente
    
    # Barra Superior
    col_logo, col_logout = st.columns([4, 1])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=150)
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.session_state.datos_cliente = None
            st.rerun()
            
    st.markdown("---")
    st.markdown(f"### Bienvenido, {cliente['Empresa']}")
    st.markdown(f"**Condiciones pre-aprobadas en {cliente['Moneda']}**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Entradas del Cliente
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        precio_input = st.number_input(f"Valor del Activo ({cliente['Moneda']})", min_value=1000.0, value=500000.0, step=10000.0)
    with col_input2:
        plazos_permitidos = [12, 24, 36, 48, 60]
        plazo_seleccionado = st.selectbox("Plazo de Arrendamiento (Meses)", plazos_permitidos, index=2)
        
    # Variables ocultas de Google Sheets
    tasa_anual = float(cliente['Tasa_Anual'])
    comision_porc = float(cliente['Comision_Apertura'])
    residual_porc = float(cliente['Valor_Residual'])
    
    # Cálculos Financieros
    precio_base = precio_input / 1.16
    tasa_mensual = (tasa_anual / 100) / 12
    monto_residual = precio_base * (residual_porc / 100)
    
    renta_neta = abs(npf.pmt(tasa_mensual, plazo_seleccionado, precio_base, -monto_residual, when=1))
    iva_renta = renta_neta * 0.16
    renta_total = renta_neta + iva_renta
    
    comision_neta = precio_base * (comision_porc / 100)
    comision_iva = comision_neta * 0.16
    comision_total = comision_neta + comision_iva
    
    pago_inicial_total = renta_total + comision_total + renta_total
    
    st.markdown("---")
    st.markdown("### Resumen de Inversión")
    
    # Tarjetas de Resumen
    m1, m2, m3 = st.columns(3)
    m1.metric("Renta Mensual (IVA incluido)", f"${renta_total:,.2f}")
    m2.metric("Pago Inicial (Firma de Contrato)", f"${pago_inicial_total:,.2f}")
    m3.metric("Plazo Forzoso", f"{plazo_seleccionado} Meses")
    
    st.info("Nota: Las rentas en el arrendamiento puro son 100% deducibles de impuestos, lo que representa un beneficio fiscal directo para su empresa.")
