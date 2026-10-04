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
    /* Oculta la barra superior de Streamlit y el botón de GitHub */
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
    """
    Valida si el nombre y los últimos 4 dígitos del teléfono coinciden en motorizados.csv
    """
    if df_motorizados.empty or 'nombre' not in df_motorizados.columns or 'telefono' not in df_motorizados.columns:
        return False, None

    nombre_clean = nombre_ingresado.strip().lower()

    for _, row in df_motorizados.iterrows():
        nombre_bd = str(row['nombre']).strip()
        telefono_bd = str(row['telefono'])
        
        # Extraer solo los números del teléfono
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
            # 1. Validar Admin desde Secrets
            usuarios_validos = st.secrets.get("passwords", {})
            user_clean = user_input.lower()
            
            if user_clean in usuarios_validos and str(usuarios_validos[user_clean]) == pass_input:
                st.session_state.autenticado = True
                st.session_state.usuario = user_clean
                st.session_state.rol = "Admin"
                st.rerun()
            else:
                # 2. Validar si es Motorizado desde motorizados.csv
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
    opciones = [
        " Registrar Vuelta", 
        " Validar Vueltas", 
        " Corte Clientes", 
        " Corte Motorizados", 
        " Directorio Clientes", 
        " Perfiles Motorizados",
        " Portal Motorizados"
    ]
else:
    opciones = [" Registrar Vuelta"]

# Cambiamos st.sidebar.radio por st.radio horizontal
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

if opcion_menu == " Portal Motorizados":
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

# --- MÓDULO: REGISTRAR VUELTA (COMPACTO) ---
elif opcion_menu == " Registrar Vuelta":
    st.subheader("⚡ Registrar Nueva Vuelta / Carrera")
    
    # Lista de clientes general
    nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []

    # 1. PARÁMETROS SUPERIORES
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

    # 2. ENTRADA DE DATOS CON FORMULARIO
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
            # Capturar la fecha del selector directamente
            if 'fecha_fija_input' in locals() and fecha_fija_input:
                fecha_str = fecha_fija_input.strftime("%Y-%m-%d")
            else:
                fecha_str = date.today().strftime("%Y-%m-%d")

            # Asignar 'Local' de forma transparente si el campo está vacío
            origen_val = origen.strip() if origen.strip() else "Local"
            destino_val = destino.strip() if destino.strip() else "Local"

            if not cli_sel:
                st.error("⚠️ Debes seleccionar un Cliente Prefijado.")
            elif origen_val.lower() == "local" and destino_val.lower() == "local":
                st.error("⚠️ No se puede registrar una vuelta de 'Local' a 'Local'. Debes especificar al menos el origen o el destino.")
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
                    st.success(f"✅ ¡Vuelta #{nuevo_id} registrada ({origen_val} ➡️ {destino_val}) para {cli_sel} con fecha {fecha_str}!")
                    st.rerun()
                else:
                    st.error("⚠️ Error al guardar en GitHub. Intenta nuevamente.")

elif opcion_menu == " Validar Vueltas":
    st.title("⚙️ Validar y Asignar Precios")
    st.caption("Revisa las vueltas precargadas por los motorizados, asigna precios o anúlalas. Consulta la tabla inferior para evitar duplicados.")

    df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)
    df_motorizados, _ = cargar_csv_desde_github(FILE_MOTORIZADOS)
    df_clientes, _ = cargar_csv_desde_github(FILE_CLIENTES)

    if df_servicios.empty:
        st.info("No hay datos registrados en servicios.")
    else:
        # --- BLINDAJE OBLIGATORIO CONTRA EL KEYERROR ---
        if 'estado_validacion' not in df_servicios.columns:
            df_servicios['estado_validacion'] = 'Pendiente'
        else:
            df_servicios['estado_validacion'] = df_servicios['estado_validacion'].fillna('Pendiente')
            
        if 'precio_cliente' not in df_servicios.columns:
            df_servicios['precio_cliente'] = 0.0
        else:
            df_servicios['precio_cliente'] = df_servicios['precio_cliente'].fillna(0.0)
        # -----------------------------------------------

        # 1. SECCIÓN: VUELTAS PENDIENTES DE VALIDACIÓN
        vueltas_pendientes = df_servicios[df_servicios['estado_validacion'] == 'Pendiente']
        st.subheader(f"📥 Vueltas Precargadas Pendientes ({len(vueltas_pendientes)})")
        
        if vueltas_pendientes.empty:
            st.success("🎉 ¡No hay vueltas pendientes por validar!")
        else:
            for idx, row in vueltas_pendientes.iterrows():
                id_v = row.get('id', idx)
                raw_fecha = row.get('fecha', '')
                fecha_v = str(raw_fecha) if pd.notna(raw_fecha) and str(raw_fecha).strip() != '' and str(raw_fecha) != 'nan' else date.today().strftime("%Y-%m-%d")
                cliente_v = str(row.get('cliente', 'Sin Cliente'))
                motorizado_v = str(row.get('motorizado', 'Sin Motorizado'))
                origen_v = str(row.get('origen', 'Local'))
                destino_v = str(row.get('destino', 'Local'))
                detalle_v = str(row.get('detalle', ''))

                with st.expander(f"📌 Vuelta #{id_v} | Fecha: {fecha_v} | Cliente: {cliente_v} | Motorizado: {motorizado_v}"):
                    c_info1, c_info2 = st.columns(2)
                    c_info1.write(f"**Origen:** {origen_v}")
                    c_info1.write(f"**Destino:** {destino_v}")
                    c_info2.write(f"**Detalle / Obs:** {detalle_v if detalle_v and detalle_v != 'nan' else 'Ninguno'}")

                    pct_comision_default = 66.67
                    if not df_motorizados.empty and 'nombre' in df_motorizados.columns:
                        match_m = df_motorizados[df_motorizados['nombre'].astype(str).str.strip().str.lower() == motorizado_v.strip().lower()]
                        if not match_m.empty and 'porcentaje_ganancia' in match_m.columns:
                            try:
                                pct_comision_default = float(match_m.iloc[0]['porcentaje_ganancia'])
                            except:
                                pass

                    st.markdown("---")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        precio_cli = st.number_input(f"Precio Cliente ($)", min_value=0.0, value=0.0, step=0.5, key=f"p_cli_{id_v}")
                    with col_p2:
                        pct_comision = st.number_input(f"% Comisión Motorizado", min_value=0.0, max_value=100.0, value=pct_comision_default, step=1.0, key=f"pct_mot_{id_v}")

                    monto_mot = round(precio_cli * (pct_comision / 100.0), 2)
                    ganancia = round(precio_cli - monto_mot, 2)
                    with col_p3:
                        st.metric("Pago Motorizado / Empresa", f"${monto_mot:.2f} / ${ganancia:.2f}")

                    btn_col1, btn_col2 = st.columns([1, 1])
                    with btn_col1:
                        if st.button("✅ Validar y Asignar", key=f"btn_val_{id_v}", use_container_width=True, type="primary"):
                            if precio_cli <= 0:
                                st.error("⚠️ Debes ingresar un precio de cliente mayor a $0.")
                            else:
                                df_servicios.loc[df_servicios['id'] == id_v, 'fecha'] = fecha_v
                                df_servicios.loc[df_servicios['id'] == id_v, 'precio_cliente'] = precio_cli
                                df_servicios.loc[df_servicios['id'] == id_v, 'porcentaje_comision'] = pct_comision
                                df_servicios.loc[df_servicios['id'] == id_v, 'monto_motorizado'] = monto_mot
                                df_servicios.loc[df_servicios['id'] == id_v, 'ganancia_empresa'] = ganancia
                                df_servicios.loc[df_servicios['id'] == id_v, 'estado_validacion'] = 'Validado'
                                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Validada vuelta #{id_v}"):
                                    st.success(f"✅ Vuelta #{id_v} validada correctamente.")
                                else:
                                    st.error("❌ Error al guardar en GitHub.")
                    with btn_col2:
                        if st.button("🚫 Anular Vuelta", key=f"btn_anular_{id_v}", use_container_width=True):
                            df_servicios.loc[df_servicios['id'] == id_v, 'estado_validacion'] = 'Anulada'
                            if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Anulada vuelta precargada #{id_v}"):
                                st.warning(f"🚫 Vuelta #{id_v} ha sido anulada.")
                                st.rerun()
                            else:
                                st.error("❌ Error al guardar en GitHub.")

        st.markdown("---")
        st.subheader("🔍 Consultar / Evaluar Vueltas Registradas")
        st.caption("Filtra las vueltas para verificar si un servicio ya fue ingresado previamente.")
        
        col_fecha1, col_fecha2 = st.columns(2)
        with col_fecha1:
            f_desde_val = st.date_input("📅 Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="f_desde_val")
        with col_fecha2:
            f_hasta_val = st.date_input("📅 Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="f_hasta_val")

        col_f1, col_f2, col_f3 = st.columns(3)
        list_mot = ["Todos"] + sorted(df_motorizados['nombre'].dropna().tolist()) if not df_motorizados.empty and 'nombre' in df_motorizados.columns else ["Todos"]
        list_cli = ["Todos"] + sorted(df_clientes['nombre'].dropna().tolist()) if not df_clientes.empty and 'nombre' in df_clientes.columns else ["Todos"]
        with col_f1:
            filtro_mot = st.selectbox("🎯 Filtrar por Motorizado", options=list_mot)
        with col_f2:
            filtro_cli = st.selectbox("👤 Filtrar por Cliente", options=list_cli)
        with col_f3:
            filtro_estado = st.selectbox("📋 Estado de Validación", options=["Todos", "Validado", "Pendiente", "Anulada"])

        df_filtrado = df_servicios.copy()
        if f_desde_val or f_hasta_val:
            fechas_dt_val = pd.to_datetime(df_filtrado['fecha'], dayfirst=True, errors='coerce').dt.date
            if f_desde_val and f_hasta_val:
                df_filtrado = df_filtrado[(fechas_dt_val >= f_desde_val) & (fechas_dt_val <= f_hasta_val)]
            elif f_desde_val:
                df_filtrado = df_filtrado[fechas_dt_val >= f_desde_val]
            elif f_hasta_val:
                df_filtrado = df_filtrado[fechas_dt_val <= f_hasta_val]

        if filtro_mot != "Todos":
            df_filtrado = df_filtrado[df_filtrado['motorizado'].astype(str).str.strip() == filtro_mot]
        if filtro_cli != "Todos":
            df_filtrado = df_filtrado[df_filtrado['cliente'].astype(str).str.strip() == filtro_cli]
        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['estado_validacion'] == filtro_estado]

        if st.button("💾 Guardar Cambios en la Tabla", type="primary"):
            df_servicios.update(df_editado)
            if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, "Actualización manual desde tabla evaluadora"):
                st.success("✅ ¡Cambios guardados exitosamente en GitHub!")
            else:
                st.error("❌ Error al guardar en GitHub.")
                
# --- MÓDULO: DIRECTORIO CLIENTES ---
elif opcion_menu == " Directorio Clientes":
    st.header("👥 Gestión y Directorio de Clientes")
    col_c1, col_c2 = st.columns([1, 1])
    
    with col_c1:
        st.subheader("➕ Agregar Nuevo Cliente")
        with st.form("form_agregar_cliente", clear_on_submit=True):
            tel_c = st.text_input("Teléfono / WhatsApp (ID Único) *").strip()
            nom_c = st.text_input("Nombre / Negocio *").strip()
            ubi_c = st.text_input("Ubicación Principal *").strip()
            btn_guardar_c = st.form_submit_button("Guardar Cliente", type="primary", use_container_width=True)
            if btn_guardar_c:
                if not tel_c or not nom_c:
                    st.error("⚠️ El teléfono y el nombre son obligatorios.")
                elif not df_clientes.empty and tel_c in df_clientes['telefono'].astype(str).values:
                    st.error(f"⚠️ El número {tel_c} ya pertenece a un cliente registrado.")
                else:
                    nueva_c = pd.DataFrame([{"id": tel_c, "nombre": nom_c, "telefono": tel_c, "ubicacion": ubi_c if ubi_c else "Local", "saldo_pendiente": 0.0}])
                    df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                        st.success(f"✅ Cliente '{nom_c}' agregado exitosamente.")
                        st.rerun()

    with col_c2:
        st.subheader("✏️ Editar Cliente Existente")
        nom_clientes_lista = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        cliente_a_editar = st.selectbox("Seleccionar Cliente a Modificar", nom_clientes_lista, index=None, placeholder="Buscar o seleccionar cliente...")
        if cliente_a_editar:
            datos_actuales = df_clientes[df_clientes['nombre'] == cliente_a_editar].iloc[0]
            with st.form("form_editar_cliente"):
                st.info(f"📱 Teléfono / ID: **{datos_actuales['telefono']}** (No editable)")
                nuevo_nombre = st.text_input("Nombre / Negocio", value=str(datos_actuales['nombre']))
                nueva_ubicacion = st.text_input("Ubicación", value=str(datos_actuales['ubicacion']))
                btn_actualizar = st.form_submit_button("Actualizar Datos", type="primary", use_container_width=True)
                if btn_actualizar:
                    idx_edit = df_clientes[df_clientes['nombre'] == cliente_a_editar].index[0]
                    df_clientes.at[idx_edit, 'nombre'] = nuevo_nombre.strip()
                    df_clientes.at[idx_edit, 'ubicacion'] = nueva_ubicacion.strip()
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Actualizado cliente {nuevo_nombre}"):
                        st.success(f"✅ Datos de '{nuevo_nombre}' actualizados correctamente.")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Lista de Clientes Registrados")
    if not df_clientes.empty:
        df_mostrar = df_clientes[['nombre', 'telefono', 'ubicacion']].copy()
        df_mostrar.columns = ["Nombre / Negocio", "Teléfono / WhatsApp", "Ubicación"]
        st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.info("No hay clientes registrados en la base de datos.")

# --- MÓDULO: PERFILES MOTORIZADOS ---
elif opcion_menu == " Perfiles Motorizados":
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

# --- MÓDULO: CORTE CLIENTES Y GESTIÓN DE VUELTAS ---
elif "Corte Clientes" in opcion_menu or "Cuentas" in opcion_menu:
    st.subheader("📊 Balance y Corte de Cuentas - Clientes")
    nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
    if not df_servicios.empty and nom_clientes:
        tab_balance, tab_gestion = st.tabs(["💰 Balance de Cuenta", "✏️ Editar / Eliminar Vueltas"])
        
        with tab_balance:
            cliente_sel = st.selectbox("Seleccionar Cliente para ver Balance:", nom_clientes, index=0)
            df_cli_all = df_servicios[df_servicios['cliente'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()].copy()
            
            st.markdown("##### 📅 Filtrar Reporte por Fechas")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_desde_c = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="f_desde_corte")
            with col_f2:
                f_hasta_c = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="f_hasta_corte")

        # --- FILTRO DE FECHAS CORREGIDO Y ROBUSTO ---
        # Convertimos la columna 'fecha' a objetos datetime de Pandas ignorando horas/formatos inconsistentes
        fechas_dt = pd.to_datetime(df_cli_all['fecha'], dayfirst=True, errors='coerce').dt.date

        if f_desde_c and f_hasta_c:
            pendientes = df_cli_all[(fechas_dt >= f_desde_c) & (fechas_dt <= f_hasta_c)].copy()
        elif f_desde_c:
            pendientes = df_cli_all[fechas_dt >= f_desde_c].copy()
        elif f_hasta_c:
            pendientes = df_cli_all[fechas_dt <= f_hasta_c].copy()
        else:
            pendientes = df_cli_all[df_cli_all['estado_cliente'] == 'Pendiente'].copy()

            def formatear_dd_mm(val):
                if pd.isna(val) or not str(val).strip() or str(val).lower() == 'none': return ""
                try:
                    dt = pd.to_datetime(val, errors='coerce')
                    if pd.notnull(dt): return dt.strftime('%d/%m')
                    parts = str(val)[:10].split('-')
                    if len(parts) == 3: return f"{parts[2]}/{parts[1]}"
                    return str(val)[:5]
                except: return str(val)[:5]

            pendientes['fecha_corta'] = pendientes['fecha'].apply(formatear_dd_mm)
            total_deuda = pendientes['precio_cliente'].astype(float).sum()

            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Pendiente por Cobrar ($)", f"${total_deuda:.2f}")
            c_m2.metric("Vueltas Filtradas / Pendientes", len(pendientes))
            st.markdown("---")

            col_abono, col_wa = st.columns([2, 1])
            with col_abono:
                abono_cliente = st.number_input("💵 Registrar Abono / Descuento ($):", min_value=0.0, max_value=float(total_deuda) if total_deuda > 0 else 0.0, value=0.0, step=0.5)
                tel_cliente = ""
                if not df_clientes.empty and 'telefono' in df_clientes.columns:
                    c_info = df_clientes[df_clientes['nombre'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()]
                    if not c_info.empty:
                        tel_cliente = str(c_info.iloc[0]['telefono']).replace("+", "").replace(" ", "").replace("-", "")
            with col_wa:
                st.write("")
                st.write("")
                if tel_cliente:
                    st.link_button("📲 Abrir Chat WhatsApp", f"https://wa.me/{tel_cliente}", use_container_width=True)
                else:
                    st.caption("⚠️ Cliente sin teléfono registrado")

            st.markdown("### 📋 Detalle de Servicios")
            if not pendientes.empty:
                st.dataframe(pendientes[['id', 'fecha_corta', 'motorizado', 'origen', 'destino', 'precio_cliente', 'estado_cliente']], use_container_width=True)

            total_neto = max(0.0, total_deuda - abono_cliente)
            msg_whatsapp = f"🧾 *REPORTE DE CUENTA - MOTOVUELTAS*\nCliente: *{cliente_sel}*\n\n"
            for f_corta in pendientes['fecha_corta'].unique():
                if f_corta:
                    msg_whatsapp += f"📅 *{f_corta}*\n"
                    for _, r in pendientes[pendientes['fecha_corta'] == f_corta].iterrows():
                        msg_whatsapp += f"▪ {r['origen']} ➡️ {r['destino']} = *${float(r['precio_cliente']):.2f}*\n"
                    msg_whatsapp += "\n"
            msg_whatsapp += "───────────────\n"
            msg_whatsapp += f"💵 *Subtotal Vueltas:* ${total_deuda:.2f}\n"
            if abono_cliente > 0:
                msg_whatsapp += f"📉 *Abono Registrado:* -${abono_cliente:.2f}\n"
            msg_whatsapp += f"💰 *TOTAL A PAGAR: ${total_neto:.2f}*"

            st.markdown("📱 **Mensaje de Control para WhatsApp:**")
            st.code(msg_whatsapp, language="text")
            st.markdown("---")

            confirmar_pago = st.checkbox(f"⚠️ Confirmar que deseas marcar estas {len(pendientes)} vueltas como PAGADAS.", key="check_pago_seguro")
            if st.button(f"✅ Marcar todas estas vueltas de {cliente_sel} como PAGADAS", type="primary", disabled=not confirmar_pago, use_container_width=True):
                ids_a_pagar = pendientes['id'].tolist()
                df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_cliente'] = 'Pagado'
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion de vueltas para {cliente_sel}"):
                    st.success(f"✅ ¡Se han marcado {len(ids_a_pagar)} vueltas de {cliente_sel} como PAGADAS correctamente!")
                    st.rerun()

        with tab_gestion:
            st.markdown("##### 🔎 Buscar y Modificar Vueltas")
            if not df_servicios.empty:
                col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 1.5, 1.5])
                nom_motos_l = df_motos['nombre'].tolist() if not df_motos.empty else []
                nom_cli_l = df_clientes['nombre'].tolist() if not df_clientes.empty else []
                with col_f1:
                    filtro_cli = st.selectbox("Cliente:", ["Todos"] + nom_cli_l, index=0, key="f_cli_tab2")
                with col_f2:
                    filtro_mot = st.selectbox("Motorizado:", ["Todos"] + nom_motos_l, index=0, key="f_mot_tab2")
                with col_f3:
                    f_desde = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="fd_tab2")
                with col_f4:
                    f_hasta = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="fh_tab2")

                df_filtrado = df_servicios.copy()

                # Convertir la columna fecha soportando formatos DD/MM/YYYY y YYYY-MM-DD
                fechas_dt = pd.to_datetime(df_filtrado['fecha'], dayfirst=True, errors='coerce')
                fechas_str = fechas_dt.dt.strftime('%Y-%m-%d').fillna(df_filtrado['fecha'].astype(str).str[:10])

                if f_desde and f_hasta:
                    df_filtrado = df_filtrado[(fechas_str >= f_desde.strftime('%Y-%m-%d')) & (fechas_str <= f_hasta.strftime('%Y-%m-%d'))]
                elif f_desde:
                    df_filtrado = df_filtrado[fechas_str == f_desde.strftime('%Y-%m-%d')]
                elif f_hasta:
                    df_filtrado = df_filtrado[fechas_str == f_hasta.strftime('%Y-%m-%d')]

                if filtro_cli and filtro_cli != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['cliente'].astype(str).str.strip().str.lower() == filtro_cli.strip().lower()]
                if filtro_mot and filtro_mot != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['motorizado'].astype(str).str.strip().str.lower() == filtro_mot.strip().lower()]

                fechas_dt_tabla = pd.to_datetime(df_filtrado['fecha'], dayfirst=True, errors='coerce')
                df_filtrado['fecha_real'] = fechas_dt_tabla.dt.strftime('%Y-%m-%d').fillna(df_filtrado['fecha'].astype(str).str.strip().str[:10])
                df_filtrado['eliminar'] = False
                st.markdown(f"**Vueltas encontradas:** {len(df_filtrado)}")

                if not df_filtrado.empty:
                    column_config = {
                        "eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False),
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "fecha_real": st.column_config.TextColumn("Fecha (AAAA-MM-DD)", help="Ejemplo: 2026-08-07"),
                        "cliente": st.column_config.SelectboxColumn("Cliente", options=nom_cli_l, required=True),
                        "motorizado": st.column_config.SelectboxColumn("Motorizado", options=nom_motos_l, required=True),
                        "origen": st.column_config.TextColumn("Desde"),
                        "destino": st.column_config.TextColumn("Hasta"),
                        "precio_cliente": st.column_config.NumberColumn("Precio ($)", format="$%.2f", min_value=0.0, step=0.5),
                        "estado_cliente": st.column_config.SelectboxColumn("Estado Pago", options=["Pendiente", "Pagado"])
                    }
                    column_order = ["eliminar", "id", "fecha_real", "cliente", "motorizado", "origen", "destino", "precio_cliente", "estado_cliente"]
                    df_editado = st.data_editor(df_filtrado[column_order], column_config=column_config, use_container_width=True, hide_index=True, key="editor_tabla_vueltas_interactivo")

                    if st.button("💾 Guardar Cambios Realizados en la Tabla", type="primary", use_container_width=True):
                        filas_eliminar = df_editado[df_editado['eliminar'] == True]['id'].tolist()
                        if filas_eliminar:
                            df_servicios = df_servicios[~df_servicios['id'].isin(filas_eliminar)].reset_index(drop=True)

                        filas_modificadas = df_editado[df_editado['eliminar'] == False]
                        for _, row in filas_modificadas.iterrows():
                            id_v = row['id']
                            idx_orig = df_servicios[df_servicios['id'] == id_v].index
                            if not idx_orig.empty:
                                i = idx_orig[0]
                                fecha_editada = str(row['fecha_real']).strip()
                                if len(fecha_editada) == 10: 
                                    fecha_editada += " 12:00"
                                df_servicios.at[i, 'fecha'] = fecha_editada
                                df_servicios.at[i, 'cliente'] = row['cliente']
                                df_servicios.at[i, 'motorizado'] = row['motorizado']
                                df_servicios.at[i, 'origen'] = row['origen']
                                df_servicios.at[i, 'destino'] = row['destino']
                                df_servicios.at[i, 'precio_cliente'] = row['precio_cliente']
                                df_servicios.at[i, 'estado_cliente'] = row['estado_cliente']

                                comision = 66.67
                                if not df_motos.empty and 'porcentaje_ganancia' in df_motos.columns:
                                    m_data = df_motos[df_motos['nombre'].astype(str).str.strip().str.lower() == str(row['motorizado']).strip().lower()]
                                    if not m_data.empty: 
                                        comision = float(m_data.iloc[0]['porcentaje_ganancia'])
                                precio = float(row['precio_cliente'])
                                m_mot = round(precio * (comision / 100.0), 2)
                                m_emp = round(precio - m_mot, 2)
                                df_servicios.at[i, 'porcentaje_comision'] = comision
                                df_servicios.at[i, 'monto_motorizado'] = m_mot
                                df_servicios.at[i, 'ganancia_empresa'] = m_emp

                        if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, "Edicion de fecha real y datos de vueltas"):
                            st.success("✅ ¡Cambios guardados correctamente!")
                            st.rerun()
            else:
                st.info("No hay servicios registrados.")
    else:
        st.info("No hay servicios registrados en la base de datos.")

# --- MÓDULO: CORTE MOTORIZADOS ---
elif opcion_menu == " Corte Motorizados":
    st.subheader("🏍️ Balance y Corte de Cuentas - Motorizados")
    nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
    
    if not df_servicios.empty and nom_motos:
        moto_sel = st.selectbox("Seleccionar Motorizado para ver Balance:", nom_motos, index=0)
        
        # 1. FILTRO DE FECHAS Y ESTADO
        st.markdown("##### 📅 Filtrar por Rango de Fechas")
        col_fm1, col_fm2, col_fm3 = st.columns([1, 1, 1])
        with col_fm1:
            f_desde_m = st.date_input("Fecha Desde (Opcional):", value=None, key="fd_moto")
        with col_fm2:
            f_hasta_m = st.date_input("Fecha Hasta (Opcional):", value=None, key="fh_moto")
        with col_fm3:
            estado_filtro_m = st.selectbox("Estado de Vueltas:", ["Pendientes", "Pagadas", "Todas"], index=0)

        # Filtrar vueltas del motorizado
        df_mot_serv = df_servicios[(df_servicios['motorizado'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower())].copy()
        
        fechas_mot_dt = pd.to_datetime(df_mot_serv['fecha'], dayfirst=True, errors='coerce')
        fechas_mot_str = fechas_mot_dt.dt.strftime('%Y-%m-%d').fillna(df_mot_serv['fecha'].astype(str).str[:10])

        if f_desde_m and f_hasta_m:
            df_mot_serv = df_mot_serv[(fechas_mot_str >= f_desde_m.strftime('%Y-%m-%d')) & (fechas_mot_str <= f_hasta_m.strftime('%Y-%m-%d'))]
        elif f_desde_m:
            df_mot_serv = df_mot_serv[fechas_mot_str == f_desde_m.strftime('%Y-%m-%d')]
        elif f_hasta_m:
            df_mot_serv = df_mot_serv[fechas_mot_str == f_hasta_m.strftime('%Y-%m-%d')]

        if estado_filtro_m == "Pendientes":
            vueltas_mo = df_mot_serv[df_mot_serv['estado_motorizado'] == 'Pendiente'].copy()
        elif estado_filtro_m == "Pagadas":
            vueltas_mo = df_mot_serv[df_mot_serv['estado_motorizado'] == 'Pagado'].copy()
        else:
            vueltas_mo = df_mot_serv.copy()

        def formatear_dd_mm(val):
            if pd.isna(val) or not str(val).strip() or str(val).lower() == 'none': return ""
            try:
                dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                if pd.notnull(dt): return dt.strftime('%d/%m')
                parts = str(val)[:10].split('-')
                if len(parts) == 3: return f"{parts[2]}/{parts[1]}"
                return str(val)[:5]
            except: return str(val)[:5]

        vueltas_mo['fecha_corta'] = vueltas_mo['fecha'].apply(formatear_dd_mm)
        total_comision = vueltas_mo['monto_motorizado'].astype(float).sum()

        # 2. FORMULARIO Y GUARDADO PERMANENTE DE AVANCES EN GITHUB
        with st.expander("💵 Registrar Avance / Adelanto de Dinero"):
            with st.form("form_avance_motorizado", clear_on_submit=True):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    f_avance = st.date_input("Fecha Avance", value=date.today())
                with col_a2:
                    monto_avance = st.number_input("Monto Avance ($)", min_value=0.0, step=0.5)
                concepto_avance = st.text_input("Concepto / Nota (ej: Gasolina, Almuerzo)", placeholder="Detalle del avance...")
                btn_avance = st.form_submit_button("Guardar Avance Permanente", type="primary")
                
                if btn_avance and monto_avance > 0:
                    nuevo_av = pd.DataFrame([{
                        "id": nuevo_id,
                        "fecha": f_avance.strftime("%Y-%m-%d"),
                        "motorizado": str(moto_sel).strip(),
                        "monto": float(monto_avance),
                        "concepto": concepto_avance if concepto_avance else "Adelanto de dinero",
                        "estado_avance": "Pendiente"
                    }])
                    df_avances_act = pd.concat([df_avances, nuevo_av], ignore_index=True)
                    if guardar_csv_en_github(FILE_AVANCES, df_avances_act, sha_avances, f"Nuevo avance a {moto_sel}"):
                        st.success(f"✅ Avance de ${monto_avance:.2f} guardado permanentemente en GitHub.")
                        st.rerun()

        # 3. CARGA DE AVANCES PERMANENTES FILTRADOS POR FECHA
        df_avances_moto = df_avances[(df_avances['motorizado'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower())].copy() if not df_avances.empty else pd.DataFrame()
        
        if not df_avances_moto.empty:
            # Convertir cualquier formato de fecha a YYYY-MM-DD
            av_dt = pd.to_datetime(df_avances_moto['fecha'], errors='coerce')
            av_str = av_dt.dt.strftime('%Y-%m-%d').fillna(df_avances_moto['fecha'].astype(str).str[:10])

            if f_desde_m and f_hasta_m:
                df_avances_moto = df_avances_moto[(av_str >= f_desde_m.strftime('%Y-%m-%d')) & (av_str <= f_hasta_m.strftime('%Y-%m-%d'))]
            elif f_desde_m:
                df_avances_moto = df_avances_moto[av_str == f_desde_m.strftime('%Y-%m-%d')]
            elif f_hasta_m:
                df_avances_moto = df_avances_moto[av_str <= f_hasta_m.strftime('%Y-%m-%d')]

            df_avances_moto['fecha_corta'] = df_avances_moto['fecha'].apply(formatear_dd_mm)
            total_avances = df_avances_moto['monto'].astype(float).sum()
        else:
            total_avances = 0.0

        saldo_neto_pagar = total_comision - total_avances

        # 4. MÉTRICAS PRINCIPALES
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Comisiones Ganadas", f"${total_comision:.2f}")
        c_m2.metric("Adelantos Registrados", f"-${total_avances:.2f}")
        c_m3.metric("🔥 Saldo Neto a Pagar", f"${saldo_neto_pagar:.2f}")
        c_m4.metric("Vueltas Encontradas", len(vueltas_mo))

        # 5. TABLA VISUAL DE ADELANTOS REGISTRADOS EN GITHUB
        if not df_avances_moto.empty:
            st.markdown("##### 💵 Adelantos / Avances Registrados en el Periodo (GitHub)")
            st.dataframe(df_avances_moto[['fecha_corta', 'monto', 'concepto']].rename(columns={
                'fecha_corta': 'Fecha',
                'monto': 'Monto ($)',
                'concepto': 'Concepto'
            }), use_container_width=True)

        st.markdown("---")

        # 6. DETALLE DE VUELTAS EDITABLE Y MENSAJE DE WHATSAPP
        st.markdown("### 📋 Detalle de Vueltas (Editable)")
        if not vueltas_mo.empty:
            # Seleccionar columnas para edición segura
            cols_editables = ['id', 'fecha_corta', 'cliente', 'origen', 'destino', 'precio_cliente', 'porcentaje_comision', 'monto_motorizado', 'estado_motorizado']
            
            # Asegurar columnas numéricas
            vueltas_mo['porcentaje_comision'] = pd.to_numeric(vueltas_mo['porcentaje_comision'], errors='coerce').fillna(66.67)
            vueltas_mo['monto_motorizado'] = pd.to_numeric(vueltas_mo['monto_motorizado'], errors='coerce').fillna(0.0)
            vueltas_mo['precio_cliente'] = pd.to_numeric(vueltas_mo['precio_cliente'], errors='coerce').fillna(0.0)

            column_config_m = {
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "fecha_corta": st.column_config.TextColumn("Fecha", disabled=True),
                "cliente": st.column_config.TextColumn("Cliente", disabled=True),
                "origen": st.column_config.TextColumn("Desde", disabled=True),
                "destino": st.column_config.TextColumn("Hasta", disabled=True),
                "precio_cliente": st.column_config.NumberColumn("Precio Cliente ($)", format="$%.2f", step=0.5),
                "porcentaje_comision": st.column_config.NumberColumn("% Ganancia Moto", min_value=0.0, max_value=100.0, step=0.5, format="%.1f%%"),
                "monto_motorizado": st.column_config.NumberColumn("Monto Motorizado ($)", format="$%.2f", step=0.1),
                "estado_motorizado": st.column_config.SelectboxColumn("Estado Pago", options=["Pendiente", "Pagado"])
            }

            vueltas_editadas = st.data_editor(
                vueltas_mo[cols_editables],
                column_config=column_config_m,
                use_container_width=True,
                hide_index=True,
                key=f"editor_vueltas_{moto_sel}"
            )

            # Botón para recalcular y guardar cambios en las vueltas editadas
            if st.button("💾 Guardar Cambios Realizados en Vueltas", type="secondary", use_container_width=True):
                for _, r_edit in vueltas_editadas.iterrows():
                    idx_v = df_servicios[df_servicios['id'] == r_edit['id']].index
                    if not idx_v.empty:
                        i = idx_v[0]
                        precio_act = float(r_edit['precio_cliente'])
                        com_act = float(r_edit['porcentaje_comision'])
                        
                        # Si cambió el precio o el porcentaje, recalcular monto
                        monto_act = float(r_edit['monto_motorizado'])
                        if com_act != float(df_servicios.at[i, 'porcentaje_comision']) or precio_act != float(df_servicios.at[i, 'precio_cliente']):
                            monto_act = round(precio_act * (com_act / 100.0), 2)

                        df_servicios.at[i, 'precio_cliente'] = precio_act
                        df_servicios.at[i, 'porcentaje_comision'] = com_act
                        df_servicios.at[i, 'monto_motorizado'] = monto_act
                        df_servicios.at[i, 'ganancia_empresa'] = round(precio_act - monto_act, 2)
                        df_servicios.at[i, 'estado_motorizado'] = r_edit['estado_motorizado']

                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Actualizadas comisiones/vueltas de {moto_sel}"):
                    st.success("✅ ¡Cambios guardados en GitHub con éxito!")
                    st.rerun()

            st.markdown("---")

            # Módulo de Teléfono y WhatsApp
            tel_moto = ""
            if not df_motos.empty and 'telefono' in df_motos.columns:
                m_info = df_motos[df_motos['nombre'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower()]
                if not m_info.empty:
                    tel_moto = str(m_info.iloc[0]['telefono']).replace("+", "").replace(" ", "").replace("-", "")

            vueltas_mo['fecha_dt'] = pd.to_datetime(vueltas_mo['fecha'], errors='coerce')
            vueltas_mo = vueltas_mo.sort_values(by='fecha_dt', ascending=True)

            msg_wa_m = f"🧾 *CORTE DE CUENTA - MOTOVUELTAS*\nMotorizado: *{moto_sel}*\n\n"
            for f_corta in vueltas_mo['fecha_corta'].unique():
                if f_corta:
                    msg_wa_m += f"📅 *{f_corta}*\n"
                    for _, r in vueltas_mo[vueltas_mo['fecha_corta'] == f_corta].iterrows():
                        msg_wa_m += f"▪ {r['origen']} ➡️ {r['destino']} = *${float(r['precio_cliente']):.2f}*\n"
                    msg_wa_m += "\n"
            
            if not df_avances_moto.empty:
                msg_wa_m += "💵 *ADELANTOS RECIBIDOS:*\n"
                for _, av_row in df_avances_moto.iterrows():
                    msg_wa_m += f"▪ {av_row['fecha_corta']}: -${float(av_row['monto']):.2f} ({av_row['concepto']})\n"
                msg_wa_m += "\n"
                
            msg_wa_m += "───────────────\n"
            msg_wa_m += f"💵 *Total Comisiones:* ${total_comision:.2f}\n"
            if total_avances > 0:
                msg_wa_m += f"📉 *Adelantos Restados:* -${total_avances:.2f}\n"
            msg_wa_m += f"💰 *TOTAL NETO A COBRAR: ${saldo_neto_pagar:.2f}*"

            col_wa_m, col_bot_m = st.columns([2, 1])
            with col_wa_m:
                st.markdown("📱 **Mensaje de Control para WhatsApp:**")
                st.code(msg_wa_m, language="text")
            with col_bot_m:
                st.write("")
                st.write("")
                if tel_moto:
                    st.link_button("📲 Abrir Chat WhatsApp", f"https://wa.me/{tel_moto}", use_container_width=True)
                else:
                    st.caption("⚠️ Motorizado sin teléfono registrado")

            st.markdown("---")

            # 7. BOTÓN PARA LIQUIDAR Y CAMBIAR ESTATUS
            confirmar_corte_m = st.checkbox(f"⚠️ Confirmar pago y cambio de status de estas {len(vueltas_mo)} vueltas a PAGADAS para {moto_sel}.", key="check_pago_moto")
            if st.button(f"✅ Liquidar y Marcar Vueltas como PAGADAS", type="primary", disabled=not confirmar_corte_m, use_container_width=True):
                ids_a_pagar = vueltas_mo['id'].tolist()
                df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_motorizado'] = 'Pagado'
    
                # Marcar también los adelantos del periodo como pagados en avances.csv
                if not df_avances_moto.empty:
                    ids_avances_pagar = df_avances_moto['id'].tolist()
                    if 'estado_avance' not in df_avances.columns:
                        df_avances['estado_avance'] = 'Pendiente'
                    df_avances.loc[df_avances['id'].isin(ids_avances_pagar), 'estado_avance'] = 'Pagado'
                    guardar_csv_en_github(FILE_AVANCES, df_avances, sha_avances, f"Adelantos liquidados de {moto_sel}")

                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion realizada a motorizado {moto_sel}"):
                    st.success(f"✅ ¡Se han liquidado {len(ids_a_pagar)} vueltas de {moto_sel} correctamente!")
                    st.rerun()
        else:
            st.info("No se encontraron vueltas con el filtro seleccionado.")
    else:
        st.info("No hay motorizados o servicios registrados.")

# --- MÓDULO INDEPENDIENTE: PORTAL MOTORIZADOS ---
def render_portal_motorizado(usuario_actual):
    st.title(f"🏍️ Portal Motorizados - {usuario_actual}")
    st.caption("Registra tus carreras y revisa tu saldo pendiente.")

    # 1. FECHA FIJA
    col_f, _ = st.columns([1, 2])
    with col_f:
        fecha_vuelta = st.date_input(
            "📅 Fecha de la vuelta", 
            value=date.today(), 
            key="fecha_fija_portal_motorizado"
        )

    st.markdown("---")

    # Carga de archivos necesaria
    df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)
    df_clientes, _ = cargar_csv_desde_github(FILE_CLIENTES)
    df_avances, _ = cargar_csv_desde_github(FILE_AVANCES)

    # 2. FORMULARIO DE PRECARGA DE VUELTA
    st.subheader("📝 Precargar Nueva Vuelta")

    with st.form("form_precargar_motorizado", clear_on_submit=True):
        st.text_input("Motorizado", value=usuario_actual, disabled=True)

        lista_cli = [""] + sorted(df_clientes['nombre'].dropna().tolist()) if not df_clientes.empty and 'nombre' in df_clientes.columns else [""]
        cliente_sel = st.selectbox("Seleccionar Cliente *", options=lista_cli, index=0)

        col_origen, col_destino = st.columns(2)
        with col_origen:
            origen_input = st.text_input("Desde / Origen", placeholder="Local")
        with col_destino:
            destino_input = st.text_input("Hasta / Destino", placeholder="Local")

        detalle_input = st.text_input("Detalle u Observación (Opcional)", placeholder="Ej: Entregar paquete")

        btn_precargar = st.form_submit_button("🚀 Precargar Vuelta", use_container_width=True)

        if btn_precargar:
            if not cliente_sel:
                st.error("⚠️ Debes seleccionar un cliente de la lista.")
            else:
                origen_final = origen_input.strip() if origen_input.strip() else "Local"
                destino_final = destino_input.strip() if destino_input.strip() else "Local"

                nuevo_id = 1 if df_servicios.empty or 'id' not in df_servicios.columns else int(df_servicios['id'].max()) + 1

                nueva_fila = {
                    'id': nuevo_id,
                    'fecha': fecha_vuelta.strftime("%Y-%m-%d"),
                    'cliente': cliente_sel,
                    'motorizado': usuario_actual,
                    'origen': origen_final,
                    'destino': destino_final,
                    'detalle': detalle_input.strip(),
                    'precio_cliente': 0.0,
                    'monto_motorizado': 0.0,
                    'ganancia_empresa': 0.0,
                    'estado_validacion': 'Pendiente',
                    'estado_cliente': 'Pendiente',
                    'estado_motorizado': 'Pendiente'
                }

                df_actualizado = pd.concat([df_servicios, pd.DataFrame([nueva_fila])], ignore_index=True)
                
                if guardar_csv_en_github(FILE_SERVICIOS, df_actualizado, sha_servicios, f"Precarga de vuelta por {usuario_actual}"):
                    st.success("✅ ¡Vuelta precargada con éxito! Enviada a administración para asignar precio.")
                    st.rerun()
                else:
                    st.error("❌ Ocurrió un error al guardar en GitHub.")

    st.markdown("---")

    # 3. BALANCE NO LIQUIDADO Y AVANCES
    st.subheader("💰 Mi Balance Acumulado (Pendiente de Cobro)")

    if not df_servicios.empty:
        df_mot = df_servicios[
            (df_servicios['motorizado'].astype(str).str.strip() == usuario_actual) & 
            (df_servicios['estado_motorizado'] == 'Pendiente')
        ]
        total_ganado = df_mot['monto_motorizado'].sum() if 'monto_motorizado' in df_mot.columns else 0.0
    else:
        total_ganado = 0.0

    total_avances = 0.0
    if not df_avances.empty and 'motorizado' in df_avances.columns and 'monto' in df_avances.columns:
        df_av_mot = df_avances[
            (df_avances['motorizado'].astype(str).str.strip() == usuario_actual) & 
            (df_avances['estado'] == 'Pendiente')
        ]
        total_avances = df_av_mot['monto'].sum()

    balance_neto = total_ganado - total_avances

    c1, c2, c3 = st.columns(3)
    c1.metric("Ganado en Vueltas", f"${total_ganado:.2f}")
    c2.metric("Adelantos / Avances", f"${total_avances:.2f}")
    c3.metric("Balance Neto a Cobrar", f"${balance_neto:.2f}")
