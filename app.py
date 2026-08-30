import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoVueltas v2", page_icon="🏍️", layout="wide")

# --- CREDENCIALES GITHUB ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "motovueltas-maker/Motovueltas-v2")
BRANCH = "main"

FILE_MOTORIZADOS = "motorizados.csv"
FILE_CLIENTES = "clientes.csv"
FILE_USUARIOS = "usuarios.csv"
FILE_SERVICIOS = "servicios.csv"

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

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = "Motorizado"

if not st.session_state.autenticado:
    st.title("🏍️ MotoVueltas - Acceso al Sistema")
    with st.form("form_login"):
        user_input = st.text_input("Usuario (ej: esneyder, omar)").strip().lower()
        pass_input = st.text_input("Contraseña", type="password").strip()
        btn_login = st.form_submit_button("Iniciar Sesión", type="primary")
        
        if btn_login:
            usuarios_validos = st.secrets.get("passwords", {})
            if user_input in usuarios_validos and str(usuarios_validos[user_input]) == pass_input:
                st.session_state.autenticado = True
                st.session_state.usuario = user_input
                st.session_state.rol = "Admin" if user_input == "esneyder" else "Motorizado"
                st.rerun()
            else:
                st.error("⚠️ Usuario o contraseña incorrectos.")
    st.stop()

# --- BARRA LATERAL (MENÚ Y PERFIL) ---
if "rol" not in st.session_state:
    st.session_state.rol = "Admin" if st.session_state.usuario == "esneyder" else "Motorizado"

st.sidebar.write(f"👤 **{st.session_state.usuario.capitalize()}** ({st.session_state.rol})")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.get("rol", "Motorizado") == "Admin":
    opciones = [" Validar Vueltas", " Registrar Vuelta", " Corte Clientes", " Corte Motorizados", " Directorio Clientes", " Perfiles Motorizados"]
else:
    opciones = [" Registrar Vuelta"]

opcion_menu = st.sidebar.radio("Módulo:", opciones)

# --- CARGA GENERAL DE DATOS ---
df_motos, sha_motos = cargar_csv_desde_github(FILE_MOTORIZADOS)
df_clientes, sha_clientes = cargar_csv_desde_github(FILE_CLIENTES)
df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)

# --- MÓDULO: REGISTRAR VUELTA (COMPACTO) ---
if opcion_menu == " Registrar Vuelta":
    st.subheader("⚡ Registrar Nueva Vuelta / Carrera")
    
    # === PARAMETROS FIJOS (FUERA DEL RECUADRO REFRESCABLE) ===
    if st.session_state.rol == "Admin":
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=datetime.today())
        with col_f2:
            nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
            mot_sel_fijo = st.selectbox("🏍️ Motorizado", nom_motos)
        with col_f3:
            # Obtener porcentaje por defecto del motorizado seleccionado
            com_def = 66.67
            if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
                com_def = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
            comision_fija = st.number_input("% Ganancia Moto", min_value=0.0, max_value=100.0, value=com_def, step=0.5)
    else:
        # Para Motorizado no Admin solo la fecha queda fuera
        col_f1, _ = st.columns([1, 2])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=datetime.today())
        mot_sel_fijo = st.session_state.usuario.capitalize()
        comision_fija = 66.67
        
        # Buscar comisión base si existe en base de datos
        if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
            comision_fija = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])

    fecha_str = fecha_fija.strftime("%Y-%m-%d")

    # === FORMULARIO QUE SE REFRESCA AL REGISTRAR ===
    with st.form("form_nueva_vuelta_compacta", clear_on_submit=True):
        nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        
        # Selección de cliente siempre vacía por defecto
        cli_sel = st.selectbox(
            "Cliente *", 
            nom_clientes, 
            index=None, 
            placeholder="Selecciona un cliente..."
        )

        # Campos en columnas compactas con texto fantasma (placeholder)
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

        btn_guardar = st.form_submit_button("🚀 Precargar / Registrar Vuelta", type="primary", use_container_width=True)

        if btn_guardar:
            if not cli_sel:
                st.error("⚠️ Debes seleccionar un cliente de la lista.")
            elif st.session_state.rol == "Admin" and precio_ingresado <= 0:
                st.error("⚠️ Por favor ingresa un precio válido mayor a 0.")
            else:
                nuevo_id = len(df_servicios) + 1 if not df_servicios.empty else 1
                hora_actual = datetime.now().strftime("%H:%M")
                fecha_completa = f"{fecha_str} {hora_actual}"

                # Lógica de Validación automática para Admin
                if st.session_state.rol == "Admin":
                    est_val = "Validado"
                    precio_val = float(precio_ingresado)
                    monto_mot = round(precio_val * (comision_fija / 100.0), 2)
                    monto_emp = round(precio_val - monto_mot, 2)
                else:
                    est_val = "Pendiente"
                    precio_val = 0.0
                    monto_mot = 0.0
                    monto_emp = 0.0

                nueva_fila = pd.DataFrame([{
                    "id": nuevo_id,
                    "fecha": fecha_completa,
                    "motorizado": mot_sel_fijo,
                    "cliente": cli_sel,
                    "origen": origen if origen else "Local",
                    "destino": destino if destino else "Local",
                    "detalle": "",
                    "precio_cliente": precio_val,
                    "porcentaje_comision": comision_fija,
                    "monto_motorizado": monto_mot,
                    "ganancia_empresa": monto_emp,
                    "estado_validacion": est_val,
                    "estado_cliente": "Pendiente",
                    "estado_motorizado": "Pendiente"
                }])

                df_servicios = pd.concat([df_servicios, nueva_fila], ignore_index=True)
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Vuelta #{nuevo_id} cargada por {st.session_state.usuario}"):
                    st.success(f"✅ Vuelta #{nuevo_id} guardada exitosamente ({est_val}).")
                    st.rerun()
                else:
                    st.error("❌ Error al guardar los datos en GitHub.")

# --- MÓDULO: VALIDAR VUELTAS (Solo Admin) ---
elif opcion_menu == " Validar Vueltas":
    st.header("⚙️ Validar y Asignar Precios")
    if not df_servicios.empty:
        pendientes = df_servicios[df_servicios['estado_validacion'] == "Pendiente"]
        if pendientes.empty:
            st.info("No hay vueltas pendientes por validar.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"Vuelta #{row['id']} - {row['motorizado']} ({row['cliente']}) - Fecha: {row['fecha']}"):
                    st.write(f"**Ruta:** {row['origen']} ➡️ {row['destino']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        precio = st.number_input(f"Precio Cliente ($) #{row['id']}", min_value=0.0, value=float(row['precio_cliente']), step=0.5)
                    with c2:
                        com_def = 66.67
                        if not df_motos.empty and row['motorizado'] in df_motos['nombre'].values:
                            com_def = float(df_motos[df_motos['nombre'] == row['motorizado']]['porcentaje_ganancia'].values[0])
                        comision = st.number_input(f"% Ganancia Motorizado #{row['id']}", min_value=0.0, max_value=100.0, value=com_def)
                    
                    if st.button(f"Confirmar y Validar #{row['id']}", type="primary"):
                        monto_mot = round(precio * (comision / 100.0), 2)
                        monto_emp = round(precio - monto_mot, 2)
                        
                        df_servicios.at[idx, 'precio_cliente'] = precio
                        df_servicios.at[idx, 'porcentaje_comision'] = comision
                        df_servicios.at[idx, 'monto_motorizado'] = monto_mot
                        df_servicios.at[idx, 'ganancia_empresa'] = monto_emp
                        df_servicios.at[idx, 'estado_validacion'] = "Validado"
                        
                        if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Validada vuelta #{row['id']}"):
                            st.success(f"Vuelta #{row['id']} validada correctamente.")
                            st.rerun()

# --- MÓDULO: DIRECTORIO Y EDICIÓN DE CLIENTES ---
elif opcion_menu == " Directorio Clientes":
    st.header("👥 Gestión y Directorio de Clientes")
    
    col_c1, col_c2 = st.columns([1, 1])
    
    # 1. FORMULARIO ULTRACOMPACTO: AGREGAR CLIENTE
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
                    nueva_c = pd.DataFrame([{
                        "id": tel_c, 
                        "nombre": nom_c, 
                        "telefono": tel_c, 
                        "ubicacion": ubi_c if ubi_c else "Local", 
                        "saldo_pendiente": 0.0
                    }])
                    df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                        st.success(f"✅ Cliente '{nom_c}' agregado exitosamente.")
                        st.rerun()

    # 2. FORMULARIO: EDITAR CLIENTE EXISTENTE (BUSCADOR VACÍO POR DEFECTO)
    with col_c2:
        st.subheader("✏️ Editar Cliente Existente")
        nom_clientes_lista = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        
        # Campo de búsqueda completamente vacío por defecto
        cliente_a_editar = st.selectbox(
            "Seleccionar Cliente a Modificar", 
            nom_clientes_lista, 
            index=None, 
            placeholder="Buscar o seleccionar cliente..."
        )
        
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
    
    # 3. TABLA VISUAL DE CLIENTES (SIN MOSTRAR ID SEPARADO)
    st.subheader("📋 Lista de Clientes Registrados")
    if not df_clientes.empty:
        # Se muestra una vista limpia con Nombre, Teléfono y Ubicación
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
            st.rerun()
