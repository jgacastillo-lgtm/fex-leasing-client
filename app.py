import streamlit as st
import pandas as pd
import numpy_financial as npf
import json
import os
import gspread
import base64
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y CONSTANTES
# ==========================================
st.set_page_config(page_title="FEX Capital - Portal de Clientes", layout="centered")

LOGO_FEX_PATH = "LOGO_FEX.png"
LOGO_CANTALOUPE_PATH = "LOGO_CANTALOUPE.png"

# REEMPLAZA ESTA LIGA CON LA URL REAL DE TU GOOGLE SHEETS
HOJA_DATOS_URL = "https://docs.google.com/spreadsheets/d/1kcspEz9Fz0q5Hz27BN-5Yyoza2yx2OmhHsl5GMFduK0/edit?usp=sharing"

# Forzar a Streamlit a no cortar los números de las métricas
st.markdown("""
<style>
[data-testid="stMetricValue"] {
    overflow: visible !important;
    white-space: normal !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource(ttl=60)
def cargar_base_datos():
    creds_dict = json.loads(st.secrets["gcp_service_account_json"])
    gc = gspread.service_account_from_dict(creds_dict)
    doc = gc.open_by_url(HOJA_DATOS_URL)
    registros = doc.sheet1.get_all_records()
    df = pd.DataFrame(registros)
    
    if 'Password' in df.columns:
        df['Password'] = df['Password'].astype(str)
        
    return df

# ==========================================
# 3. CLASE PARA GENERACIÓN DE PDF
# ==========================================
class CotizacionPDF(FPDF):
    def header(self):
        # Logo FEX (Izquierda Superior)
        if os.path.exists(LOGO_FEX_PATH):
            self.image(LOGO_FEX_PATH, x=10, y=10, w=35)
            
        # Logo Cantaloupe (Izquierda Inferior, debajo de FEX)
        if os.path.exists(LOGO_CANTALOUPE_PATH):
            # Se le da un ancho mayor (w=55) porque es un logo muy horizontal
            self.image(LOGO_CANTALOUPE_PATH, x=10, y=20, w=55)
            
        # Se baja el inicio del texto para no encimarse con los logos apilados
        self.set_y(38)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(27, 27, 27) 
        self.cell(0, 6, 'Cotización Preliminar de Arrendamiento Puro', 0, 1, 'C')
        
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Fecha: {fecha_hoy}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# ==========================================
# 4. GESTIÓN DE SESIÓN (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.datos_cliente = None

# ==========================================
# 5. PANTALLA DE ACCESO
# ==========================================
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Apilamos ambos logos en la pantalla de inicio de sesión
        if os.path.exists(LOGO_FEX_PATH):
            st.image(LOGO_FEX_PATH, use_container_width=True)
        if os.path.exists(LOGO_CANTALOUPE_PATH):
            st.image(LOGO_CANTALOUPE_PATH, use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; color: #1B1B1B; margin-top: 20px;'>Portal de Arrendamiento</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        password_input = st.text_input("Código de Acceso", type="password", placeholder="Ingresa tu clave corporativa")
        
        if st.button("Ingresar al Cotizador", use_container_width=True):
            if password_input:
                try:
                    df_clientes = cargar_base_datos()
                    cliente_match = df_clientes[df_clientes['Password'] == str(password_input)]
                    
                    if not cliente_match.empty:
                        st.session_state.datos_cliente = cliente_match.iloc[0].to_dict()
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("Código de acceso incorrecto. Verifica con tu ejecutivo de FEX Capital.")
                except Exception as e:
                    st.error(f"Detalle técnico del error: {e}")
            else:
                st.warning("Por favor, ingresa un código válido.")

# ==========================================
# 6. PANTALLA DEL COTIZADOR VIP
# ==========================================
else:
    cliente = st.session_state.datos_cliente
    moneda = cliente['Moneda']
    
    # Barra Superior (Logos apilados a la izquierda y Logout a la derecha)
    col_logos, col_vacio, col_logout = st.columns([3, 5, 2])
    with col_logos:
        if os.path.exists(LOGO_FEX_PATH):
            st.image(LOGO_FEX_PATH, use_container_width=True)
        if os.path.exists(LOGO_CANTALOUPE_PATH):
            st.image(LOGO_CANTALOUPE_PATH, use_container_width=True)
            
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.datos_cliente = None
            st.rerun()
            
    st.markdown("---")
    st.markdown(f"### Bienvenido, {cliente['Empresa']}")
    st.markdown(f"**Condiciones pre-aprobadas en {moneda}**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Entradas del Cliente
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        precio_input = st.number_input(f"Valor del Activo ({moneda})", min_value=1000.0, value=500000.0, step=10000.0)
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
    m1.metric(f"Renta Mensual ({moneda})", f"${renta_total:,.2f}")
    m2.metric(f"Pago Inicial a la Firma ({moneda})", f"${pago_inicial_total:,.2f}")
    m3.metric("Plazo Forzoso", f"{plazo_seleccionado} Meses")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Notas Legales en pantalla (Discretas)
    st.markdown("""
    <div style='font-size: 0.85em; color: #7f8c8d; line-height: 1.5; padding: 10px; border-left: 3px solid #e0e0e0;'>
        <strong>NOTAS IMPORTANTES:</strong><br>
        1) Esta cotización es de carácter informativo, no representa un compromiso de financiamiento.<br>
        2) Sujeta a aprobación final por parte del Comité de Crédito de FEX Capital SA de CV.<br>
        3) Las rentas en el arrendamiento puro son deducibles de impuestos de acuerdo a la legislación vigente.<br>
        4) El Pago Inicial contempla la primera renta, renta en garantía y comisión por apertura.
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 7. GENERACIÓN DEL PDF B2B
    # ==========================================
    st.markdown("---")
    if st.button("Generar y Descargar Cotización PDF"):
        pdf = CotizacionPDF()
        pdf.add_page()
        pdf.set_text_color(27, 27, 27)
        
        # 1. INFORMACIÓN DEL CLIENTE Y ACTIVO
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "1. INFORMACIÓN GENERAL", ln=True, border='B')
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Cliente: {cliente['Empresa']}", 0, 0)
        pdf.cell(95, 7, f"Plazo Forzoso: {plazo_seleccionado} Meses", 0, 1)
        pdf.cell(0, 7, f"Valor del Activo (IVA inc): {moneda} ${precio_input:,.2f}", 0, 1)
        pdf.ln(5)

        # 2. RESUMEN FINANCIERO COMERCIAL
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "2. RESUMEN FINANCIERO", ln=True, border='B')
        pdf.ln(3)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Renta Mensual (IVA inc):", 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, f"{moneda} ${renta_total:,.2f}", 0, 1)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Pago Inicial (Firma de Contrato):", 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, f"{moneda} ${pago_inicial_total:,.2f}", 0, 1)
        pdf.ln(5)

        # 3. NOTAS LEGALES
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, "NOTAS IMPORTANTES:", ln=True)
        pdf.cell(0, 5, "1) Esta cotización es de carácter informativo, no representa un compromiso de financiamiento.", ln=True)
        pdf.cell(0, 5, "2) Sujeta a aprobación final por parte del Comité de Crédito de FEX Capital SA de CV.", ln=True)
        pdf.cell(0, 5, "3) Las rentas en el arrendamiento puro son deducibles de impuestos de acuerdo a la legislación vigente.", ln=True)
        pdf.cell(0, 5, "4) El Pago Inicial contempla la primera renta, renta en garantía y comisión por apertura.", ln=True)

        # FIRMAS
        pdf.ln(20)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(90, 10, "__________________________________", 0, 0, 'C'); pdf.cell(90, 10, "__________________________________", 0, 1, 'C')
        pdf.cell(90, 5, f"Por: {cliente['Empresa']}", 0, 0, 'C'); pdf.cell(90, 5, "Por: FEX CAPITAL, S.A. DE C.V.", 0, 1, 'C')

        # Descarga clásica FPDF
        pdf_output = pdf.output(dest='S').encode('latin-1')
        b64_pdf = base64.b64encode(pdf_output).decode('utf-8')
        
        st.markdown(f'<a href="data:application/pdf;base64,{b64_pdf}" download="Cotizacion_Arrendamiento_{cliente["Empresa"]}.pdf" style="padding:12px 20px; background-color:#0163FF; color:white; font-weight:bold; border-radius:4px; text-decoration:none; display:inline-block;">📥 Descargar Documento PDF</a>', unsafe_allow_html=True)
