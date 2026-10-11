import streamlit as st
import pandas as pd
import requests
import base64
import re
from datetime import datetime, date

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoVueltas v2", page_icon="🏍️", layout="wide")

# --- OCULTAR ELEMENTOS DE CABECERA (BOTÓN DE GITHUB Y MENÚS) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CREDENCIALES GITHUB ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "motovueltas-maker/Motovueltas-v2")
BRANCH = "main"

FILE_MOTORIZADOS = "motorizados.csv"
FILE_CLIENTES = "clientes.csv"
FILE_USUARIOS = "usuarios.csv"
FILE_SERVICIOS = "servicios.csv"
FILE_AVANCES = "avances.csv"

headers_gh = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- FUNCIONES DE PERSISTENCIA GITHUB ---
def cargar_csv_desde_github(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}?ref={BRANCH}"
    r = requests.get(url, headers=headers_gh)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        from io import StringIO
        df = pd.read_csv(StringIO(content))
        df.columns = [c.strip().lower() for c in df.columns]
        return df, r.json()['sha']
    else:
        return pd.DataFrame(), None

def guardar_csv_en_github(file_path, df, sha_actual, mensaje_commit):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    csv_data = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
    data = {
        "message": mensaje_commit,
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha_actual:
        data["sha"] = sha_actual
    r = requests.put(url, json=data, headers=headers_gh)
    return r.status_code in [200, 201]

def autenticar_motorizado(nombre_ingresado, clave_ingresada, df_motorizados):
    if df_motorizados.empty or 'nombre' not in df_motorizados.columns or 'telefono' not in df_motorizados.columns:
        return False, None
    nombre_clean = nombre_ingresado.strip().lower()
    for _, row in df_motorizados.iterrows():
        nombre_bd = str(row['nombre']).strip()
        telefono_bd = str(row['telefono'])
        numeros_tel = re.sub(r'\D', '', telefono_bd)
        ultimos_4 = numeros_tel[-4:] if len(numeros_tel) >= 4 else ""
        if nombre_bd.lower() == nombre_clean and clave_ingresada.strip() == ultimos_4:
            return True, nombre_bd
    return False, None

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = "Motorizado"

if not st.session_state.autenticado:
    st.title("🏍️ MotoVueltas - Acceso al Sistema")
    df_mot_login, _ = cargar_csv_desde_github(FILE_MOTORIZADOS)

    with st.form("form_login"):
        user_input = st.text_input("Usuario (ej: esneyder, Alirio)").strip()
        pass_input = st.text_input("Contraseña", type="password").strip()
        btn_login = st.form_submit_button("Iniciar Sesión", type="primary")

        if btn_login:
            usuarios_validos = st.secrets.get("passwords", {})
            user_clean = user_input.lower()
            if user_clean in usuarios_validos and str(usuarios_validos[user_clean]) == pass_input:
                st.session_state.autenticado = True
                st.session_state.usuario = user_clean
                st.session_state.rol = "Admin"
                st.rerun()
            else:
                es_valido, nombre_bd = autenticar_motorizado(user_input, pass_input, df_mot_login)
                if es_valido:
                    st.session_state.autenticado = True
                    st.session_state.usuario = nombre_bd
                    st.session_state.rol = "Motorizado"
                    st.rerun()
                else:
                    st.error("⚠️ Usuario o contraseña incorrectos.")
    st.stop()

# --- MENÚ SUPERIOR DE NAVEGACIÓN ---
if st.session_state.get("rol", "Motorizado") == "Admin":
    opciones = ["Registrar Vuelta", "Validar Vueltas", "Corte Clientes", "Corte Motorizados", "Directorio Clientes", "Perfiles Motorizados", "Portal Motorizados"]
else:
    opciones = ["Registrar Vuelta", "Portal Motorizados"]

opcion_menu = st.radio("📌 Menú de Módulos:", opciones, horizontal=True)
st.divider()

# --- CARGA GENERAL DE DATOS ---
df_motos, sha_motos = cargar_csv_desde_github(FILE_MOTORIZADOS)
df_clientes, sha_clientes = cargar_csv_desde_github(FILE_CLIENTES)
df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)
df_avances, sha_avances = cargar_csv_desde_github(FILE_AVANCES)

if df_avances.empty:
    df_avances = pd.DataFrame(columns=['id', 'fecha', 'motorizado', 'monto', 'concepto', 'estado_avance'])
elif 'estado_avance' not in df_avances.columns:
    df_avances['estado_avance'] = 'Pendiente'


# --- MÓDULO INDEPENDIENTE: PORTAL MOTORIZADOS (DEFINICIÓN DE FUNCIÓN) ---
def render_portal_motorizado(nombre_motorizado):
    st.subheader(f"🏍️ Panel de Control - {nombre_motorizado.capitalize()}")
    df_servicios_p, sha_s_p = cargar_csv_desde_github(FILE_SERVICIOS)
    df_motos_p, _ = cargar_csv_desde_github(FILE_MOTORIZADOS)
    df_clientes_p, _ = cargar_csv_desde_github(FILE_CLIENTES)
    df_avances_p, _ = cargar_csv_desde_github(FILE_AVANCES)

    st.markdown("### 📊 Tu Balance y Resumen")
    servicios_chofer = df_servicios_p[df_servicios_p['motorizado'].astype(str).str.strip().str.lower() == nombre_motorizado.strip().lower()].copy() if not df_servicios_p.empty and 'motorizado' in df_servicios_p.columns else pd.DataFrame()
    avances_chofer = df_avances_p[df_avances_p['motorizado'].astype(str).str.strip().str.lower() == nombre_motorizado.strip().lower()].copy() if not df_avances_p.empty and 'motorizado' in df_avances_p.columns else pd.DataFrame()

    total_comisiones = servicios_chofer['monto_motorizado'].astype(float).sum() if not servicios_chofer.empty and 'monto_motorizado' in servicios_chofer.columns else 0.0
    total_avances = avances_chofer['monto'].astype(float).sum() if not avances_chofer.empty and 'monto' in avances_chofer.columns else 0.0
    saldo_neto = total_comisiones - total_avances
    cantidad_vueltas = len(servicios_chofer)

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Comisiones Ganadas", f"${total_comisiones:.2f}")
    col_m2.metric("Adelantos", f"-${total_avances:.2f}")

    col_m3, col_m4 = st.columns(2)
    col_m3.metric("🔥 Saldo Neto a Pagar", f"${saldo_neto:.2f}")
    col_m4.metric("Vueltas Realizadas", cantidad_vueltas)

    st.markdown("---")
    st.subheader("⚡ Registrar / Precargar Nueva Vuelta")
    porcentaje_motorizado = 66.67
    if not df_motos_p.empty and 'nombre' in df_motos_p.columns:
        match_m = df_motos_p[df_motos_p['nombre'].astype(str).str.strip().str.lower() == nombre_motorizado.strip().lower()]
        if not match_m.empty and 'porcentaje_ganancia' in match_m.columns:
            porcentaje_motorizado = float(match_m['porcentaje_ganancia'].values[0])

    nom_clientes = sorted(df_clientes_p['nombre'].dropna().tolist()) if not df_clientes_p.empty and 'nombre' in df_clientes_p.columns else []

    with st.form("form_portal_motorizado_vueltas", clear_on_submit=True):
        f_vuelta = st.date_input("📅 Fecha de la Vuelta", value=date.today())
        cli_portal = st.selectbox("👤 Seleccionar Cliente *", options=[""] + nom_clientes, index=0, placeholder="Selecciona el cliente...")
        c1, c2 = st.columns(2)
        with c1:
            orig = st.text_input("Desde (Origen)", placeholder="Local")
        with c2:
            dest = st.text_input("Hasta (Destino)", placeholder="Local")
        btn_reg_portal = st.form_submit_button("🚀 Enviar Vuelta a Validación", type="primary", use_container_width=True)
        
        if btn_reg_portal:
            if not cli_portal:
                st.error("⚠️ Debes seleccionar un cliente.")
            else:
                fecha_s = f_vuelta.strftime("%Y-%m-%d")
                origen_v = orig.strip() if orig.strip() else "Local"
                destino_v = dest.strip() if dest.strip() else "Local"
                nuevo_id = int(df_servicios_p['id'].max()) + 1 if not df_servicios_p.empty and 'id' in df_servicios_p.columns else 1
                
                nueva_vuelta = pd.DataFrame([{
                    "id": nuevo_id,
                    "fecha": fecha_s,
                    "motorizado": nombre_motorizado.capitalize(),
                    "cliente": cli_portal,
                    "origen": origen_v,
                    "destino": destino_v,
                    "precio_cliente": 0.0,
                    "porcentaje_comision": porcentaje_motorizado,
                    "monto_motorizado": 0.0,
                    "ganancia_empresa": 0.0,
                    "estado_cliente": "Pendiente",
                    "estado_motorizado": "Pendiente",
                    "estado_validacion": "Pendiente"
                }])
                df_servicios_actualizado = pd.concat([df_servicios_p, nueva_vuelta], ignore_index=True)
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios_actualizado, sha_s_p, f"Vuelta #{nuevo_id} precargada por {nombre_motorizado}"):
                    st.success("✅ ¡Vuelta registrada con éxito y enviada a pendientes!")
                    st.rerun()
                else:
                    st.error("❌ Error al guardar en GitHub.")


# --- ENRUTAMIENTO DE MÓDULOS ---

if opcion_menu == "Portal Motorizados":
    if 'usuario_motorizado' not in st.session_state:
        st.session_state['usuario_motorizado'] = None

    if st.session_state['usuario_motorizado'] is None:
        st.subheader("🔑 Inicio de Sesión Motorizados")
        df_mot_login, _ = cargar_csv_desde_github(FILE_MOTORIZADOS)
        with st.form("form_login_motorizado"):
            usr_input = st.text_input("Nombre de Usuario (ej: Alirio)")
            pwd_input = st.text_input("Contraseña (4 dígitos del celular)", type="password")
            btn_login = st.form_submit_button("Ingresar")
            if btn_login:
                es_valido, nombre_bd = autenticar_motorizado(usr_input, pwd_input, df_mot_login)
                if es_valido:
                    st.session_state['usuario_motorizado'] = nombre_bd
                    st.rerun()
                else:
                    st.error("❌ Nombre de usuario o contraseña incorrectos.")
    else:
        if st.button("🚪 Cerrar Sesión Motorizado"):
            st.session_state['usuario_motorizado'] = None
            st.rerun()
        render_portal_motorizado(st.session_state['usuario_motorizado'])

# --- MÓDULO: REGISTRAR VUELTA ---
elif opcion_menu == "Registrar Vuelta":
    st.subheader("⚡ Registrar Nueva Vuelta / Carrera")
    nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []

    if st.session_state.rol == "Admin":
        col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])
        with col_f1:
            fecha_fija_input = st.date_input("📅 Fecha", value=date.today(), key="fecha_registro_key")
        with col_f2:
            nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
            mot_sel_fijo = st.selectbox("🏍️ Motorizado", nom_motos)
        with col_f3:
            cli_sel = st.selectbox("👤 Cliente Prefijado *", nom_clientes, index=None, placeholder="Selecciona...")
        with col_f4:
            com_def = 66.67
            if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
                com_def = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
            comision_fija = st.number_input("% Ganancia Moto", min_value=0.0, max_value=100.0, value=com_def, step=0.5)
    else:
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            fecha_fija_input = st.date_input("📅 Fecha", value=date.today(), key="fecha_registro_key")
            mot_sel_fijo = st.session_state.usuario.capitalize()
            comision_fija = 66.67
            if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
                comision_fija = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
        with col_f2:
            cli_sel = st.selectbox("👤 Cliente Prefijado *", nom_clientes, index=None, placeholder="Selecciona...")

    st.markdown("---")
    with st.form("form_registro_vuelta_directo", clear_on_submit=True):
        if st.session_state.rol == "Admin":
            c_orig, c_dest, c_prec = st.columns([1, 1, 1])
            with c_orig:
                origen = st.text_input("Desde", placeholder="Local")
            with c_dest:
                destino = st.text_input("Hasta", placeholder="Local")
            with c_prec:
                precio_ingresado = st.number_input("Precio ($) *", min_value=0.0, step=0.5, value=0.0)
        else:
            c_orig, c_dest = st.columns(2)
            with c_orig:
                origen = st.text_input("Desde", placeholder="Local")
            with c_dest:
                destino = st.text_input("Hasta", placeholder="Local")
            precio_ingresado = 0.0

        btn_registro = st.form_submit_button("🚀 Precargar / Registrar Vuelta", type="primary", use_container_width=True)

        if btn_registro:
            fecha_str = fecha_fija_input.strftime("%Y-%m-%d") if 'fecha_fija_input' in locals() and fecha_fija_input else date.today().strftime("%Y-%m-%d")
            origen_val = origen.strip() if origen.strip() else "Local"
            destino_val = destino.strip() if destino.strip() else "Local"

            if not cli_sel:
                st.error("⚠️ Debes seleccionar un Cliente Prefijado.")
            elif origen_val.lower() == "local" and destino_val.lower() == "local":
                st.error("⚠️ No se puede registrar una vuelta de 'Local' a 'Local'.")
            else:
                if st.session_state.rol == "Admin":
                    monto_mot = round(precio_ingresado * (comision_fija / 100.0), 2)
                    monto_emp = round(precio_ingresado - monto_mot, 2)
                    estado_val = "Validado"
                else:
                    monto_mot = 0.0
                    monto_emp = 0.0
                    estado_val = "Pendiente"

                nuevo_id = int(df_servicios['id'].max()) + 1 if not df_servicios.empty and 'id' in df_servicios.columns else 1
                nueva_vuelta = pd.DataFrame([{
                    "id": nuevo_id,
                    "fecha": fecha_str,
                    "motorizado": str(mot_sel_fijo).strip() if mot_sel_fijo else "",
                    "cliente": cli_sel,
                    "origen": origen_val,
                    "destino": destino_val,
                    "precio_cliente": precio_ingresado,
                    "porcentaje_comision": comision_fija,
                    "monto_motorizado": monto_mot,
                    "ganancia_empresa": monto_emp,
                    "estado_cliente": "Pendiente",
                    "estado_motorizado": "Pendiente",
                    "estado_validacion": estado_val
                }])
                df_servicios = pd.concat([df_servicios, nueva_vuelta], ignore_index=True)
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Nueva vuelta #{nuevo_id} para {cli_sel}"):
                    st.success(f"✅ ¡Vuelta #{nuevo_id} registrada ({origen_val} ➡️ {destino_val}) para {cli_sel}!")
                    st.rerun()
                else:
                    st.error("⚠️ Error al guardar en GitHub.")

# --- MÓDULO: VALIDAR VUELTAS ---
elif opcion_menu == "Validar Vueltas":
    st.title("⚙️ Validar y Asignar Precios")
    st.caption("Edita directamente el precio y la comisión en la tabla.")
    
    if df_servicios.empty:
        st.info("No hay datos registrados en servicios.")
    else:
        if 'estado_validacion' not in df_servicios.columns:
            df_servicios['estado_validacion'] = 'Pendiente'
        vueltas_pendientes = df_servicios[df_servicios['estado_validacion'] == 'Pendiente'].copy()
        st.subheader(f"📥 Vueltas Precargadas Pendientes ({len(vueltas_pendientes)})")
        
        if vueltas_pendientes.empty:
            st.success("🎉 ¡No hay vueltas pendientes por validar!")
        else:
            df_edit_pendientes = st.data_editor(vueltas_pendientes, num_rows="fixed", use_container_width=True, key="tabla_editor_pendientes_directa")
            if st.button("💾 Procesar y Guardar Cambios", type="primary"):
                for idx, row in df_edit_pendientes.iterrows():
                    p_cli = float(row.get('precio_cliente', 0.0) or 0.0)
                    p_com = float(row.get('porcentaje_comision', 66.67) or 66.67)
                    m_mot = round(p_cli * (p_com / 100.0), 2)
                    g_emp = round(p_cli - m_mot, 2)
                    estado_act = str(row.get('estado_validacion', 'Pendiente'))
                    if p_cli > 0 and estado_act == 'Pendiente':
                        estado_act = 'Validado'
                    vuelta_id = row['id']
                    df_servicios.loc[df_servicios['id'] == vuelta_id, 'precio_cliente'] = p_cli
                    df_servicios.loc[df_servicios['id'] == vuelta_id, 'porcentaje_comision'] = p_com
                    df_servicios.loc[df_servicios['id'] == vuelta_id, 'monto_motorizado'] = m_mot
                    df_servicios.loc[df_servicios['id'] == vuelta_id, 'ganancia_empresa'] = g_emp
                    df_servicios.loc[df_servicios['id'] == vuelta_id, 'estado_validacion'] = estado_act

                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, "Validación masiva"):
                    st.success("✅ ¡Cambios guardados correctamente!")
                    st.rerun()

# --- MÓDULO: DIRECTORIO CLIENTES ---
elif opcion_menu == "Directorio Clientes":
    st.header("👥 Gestión y Directorio de Clientes")
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        st.subheader("➕ Agregar Nuevo Cliente")
        with st.form("form_agregar_cliente", clear_on_submit=True):
            tel_c = st.text_input("Teléfono / WhatsApp (ID Único) *").strip()
            nom_c = st.text_input("Nombre / Negocio *").strip()
            ubi_c = st.text_input("Ubicación Principal *").strip()
            if st.form_submit_button("Guardar Cliente", type="primary", use_container_width=True):
                if not tel_c or not nom_c:
                    st.error("⚠️ El teléfono y el nombre son obligatorios.")
                else:
                    nueva_c = pd.DataFrame([{"id": tel_c, "nombre": nom_c, "telefono": tel_c, "ubicacion": ubi_c if ubi_c else "Local", "saldo_pendiente": 0.0}])
                    df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                        st.success(f"✅ Cliente '{nom_c}' agregado exitosamente.")
                        st.rerun()
    with col_c2:
        st.subheader("📋 Lista de Clientes")
        if not df_clientes.empty:
            st.dataframe(df_clientes[['nombre', 'telefono', 'ubicacion']], use_container_width=True)

# --- MÓDULO: PERFILES MOTORIZADOS ---
elif opcion_menu == "Perfiles Motorizados":
    st.header("🏍️ Gestión de Motorizados")
    if not df_motos.empty:
        st.dataframe(df_motos, use_container_width=True)
    with st.form("form_agregar_moto", clear_on_submit=True):
        st.subheader("➕ Agregar Motorizado")
        nom_m = st.text_input("Nombre del Chofer")
        tel_m = st.text_input("Teléfono")
        com_m = st.number_input("% Ganancia Base", value=66.67)
        if st.form_submit_button("Guardar Motorizado") and nom_m:
            nuevo_id_m = len(df_motos) + 1 if not df_motos.empty else 1
            nueva_m = pd.DataFrame([{"id": nuevo_id_m, "nombre": nom_m, "telefono": tel_m, "porcentaje_ganancia": com_m, "saldo_pendiente": 0.0}])
            df_motos = pd.concat([df_motos, nueva_m], ignore_index=True)
            guardar_csv_en_github(FILE_MOTORIZADOS, df_motos, sha_motos, f"Nuevo motorizado {nom_m}")
            st.rerun()

# --- MÓDULO: CORTE CLIENTES ---
elif "Corte Clientes" in opcion_menu or "Cuentas" in opcion_menu:
    st.subheader("📊 Balance y Corte de Cuentas - Clientes")
    nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
    if not df_servicios.empty and nom_clientes:
        cliente_sel = st.selectbox("Seleccionar Cliente para ver Balance:", nom_clientes, index=0)
        df_cli_all = df_servicios[df_servicios['cliente'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()].copy()
        
        pendientes = df_cli_all[df_cli_all['estado_cliente'] == 'Pendiente'].copy()
        total_deuda = pendientes['precio_cliente'].astype(float).sum()
        st.metric("Pendiente por Cobrar ($)", f"${total_deuda:.2f}")

        if not pendientes.empty:
            st.dataframe(pendientes[['id', 'fecha', 'origen', 'destino', 'precio_cliente']], use_container_width=True)
            if st.button("✅ Marcar todas estas vueltas como PAGADAS", type="primary"):
                ids_a_pagar = pendientes['id'].tolist()
                df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_cliente'] = 'Pagado'
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion para {cliente_sel}"):
                    st.success("✅ ¡Vueltas marcadas como pagadas!")
                    st.rerun()

# --- MÓDULO: CORTE MOTORIZADOS ---
elif opcion_menu == "Corte Motorizados":
    st.subheader("🏍️ Balance y Corte de Cuentas - Motorizados")
    nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
    if not df_servicios.empty and nom_motos:
        moto_sel = st.selectbox("Seleccionar Motorizado:", nom_motos, index=0)
        vueltas_mo = df_servicios[(df_servicios['motorizado'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower()) & (df_servicios['estado_motorizado'] == 'Pendiente')].copy()
        
        total_comision = vueltas_mo['monto_motorizado'].astype(float).sum()
        st.metric("Comisiones Pendientes ($)", f"${total_comision:.2f}")
        if not vueltas_mo.empty:
            st.dataframe(vueltas_mo[['id', 'fecha', 'cliente', 'origen', 'destino', 'monto_motorizado']], use_container_width=True)
