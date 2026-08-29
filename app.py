import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoVueltas v2", page_icon="🏍️", layout="wide")

# --- CREDENCIALES GITHUB (Desde Streamlit Secrets o Variables) ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "motovueltas-maker/Motovueltas-v2")
BRANCH = "main"

# Nombres de archivos CSV
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

# --- INICIALIZACIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.nombre = ""
    st.session_state.rol = ""

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("🏍️ MotoVueltas - Acceso al Sistema")
    df_users, _ = cargar_csv_desde_github(FILE_USUARIOS)
    
    with st.form("form_login"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        btn_login = st.form_submit_button("Iniciar Sesión", type="primary")
        
        if btn_login:
            if not df_users.empty and 'usuario' in df_users.columns:
                user_row = df_users[(df_users['usuario'].astype(str) == user_input) & (df_users['clave'].astype(str) == pass_input)]
                if not user_row.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = user_input
                    st.session_state.nombre = user_row.iloc[0]['nombre']
                    st.session_state.rol = user_row.iloc[0]['rol']
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.error("Error al cargar la base de datos de usuarios.")
                # Imprime el contenido para ver por qué vino vacío
                st.write("Estado actual de df_users:", df_users)

# --- BARRA LATERAL (MENÚ Y PERFIL) ---
st.sidebar.write(f"👤 **{st.session_state.nombre}** ({st.session_state.rol})")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.rol == "Admin":
    opciones = [" Validar Vueltas", " Registrar Vuelta", " Corte Clientes", " Corte Motorizados", " Directorio Clientes", " Perfiles Motorizados"]
else:
    opciones = [" Registrar Vuelta"]

opcion_menu = st.sidebar.radio("Módulo:", opciones)

# --- CARGA GENERAL DE DATOS ---
df_motos, sha_motos = cargar_csv_desde_github(FILE_MOTORIZADOS)
df_clientes, sha_clientes = cargar_csv_desde_github(FILE_CLIENTES)
df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)

# --- MÓDULO 1: REGISTRAR VUELTA ---
if opcion_menu == " Registrar Vuelta":
    st.header("➕ Registrar Nueva Vuelta / Carrera")
    
    with st.form("form_nueva_vuelta", clear_on_submit=True):
        if st.session_state.rol == "Admin":
            nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
            mot_sel = st.selectbox("Motorizado", nom_motos)
        else:
            mot_sel = st.session_state.nombre
            
        nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else ["Cliente General"]
        cli_sel = st.selectbox("Cliente", nom_clientes)
        
        origen = st.text_input("Origen")
        destino = st.text_input("Destino")
        detalle = st.text_area("Detalles / Observaciones")
        
        btn_guardar = st.form_submit_button("Guardar Vuelta", type="primary")
        
        if btn_guardar:
            if not origen or not destino:
                st.error("El origen y destino son obligatorios.")
            else:
                nuevo_id = len(df_servicios) + 1 if not df_servicios.empty else 1
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                nueva_fila = pd.DataFrame([{
                    "id": nuevo_id,
                    "fecha": fecha_actual,
                    "motorizado": mot_sel,
                    "cliente": cli_sel,
                    "origen": origen,
                    "destino": destino,
                    "detalle": detalle,
                    "precio_cliente": 0.0,
                    "porcentaje_comision": 66.67,
                    "monto_motorizado": 0.0,
                    "ganancia_empresa": 0.0,
                    "estado_validacion": "Pendiente",
                    "estado_cliente": "Pendiente",
                    "estado_motorizado": "Pendiente"
                }])
                
                df_servicios = pd.concat([df_servicios, nueva_fila], ignore_index=True)
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Nueva vuelta #{nuevo_id}"):
                    st.success("✅ Vuelta registrada exitosamente (Pendiente de Validación).")
                    st.rerun()
                else:
                    st.error("Error al guardar en GitHub.")

# --- MÓDULO 2: VALIDAR VUELTAS (Solo Admin) ---
elif opcion_menu == " Validar Vueltas":
    st.header("⚙️ Validar y Asignar Precios")
    
    if not df_servicios.empty:
        pendientes = df_servicios[df_servicios['estado_validacion'] == "Pendiente"]
        if pendientes.empty:
            st.info("No hay vueltas pendientes por validar.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"Vuelta #{row['id']} - {row['motorizado']} ({row['cliente']})"):
                    st.write(f"**Fecha:** {row['fecha']} | **Ruta:** {row['origen']} ➡️ {row['destino']}")
                    st.write(f"**Detalle:** {row['detalle']}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        precio = st.number_input(f"Precio Cliente ($) #{row['id']}", min_value=0.0, value=float(row['precio_cliente']), step=0.5)
                    with c2:
                        # Obtener comision base del motorizado
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

# --- MÓDULO 3: DIRECTORIO CLIENTES ---
elif opcion_menu == " Directorio Clientes":
    st.header("👥 Gestión de Clientes")
    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True)
        
    with st.form("form_agregar_cliente", clear_on_submit=True):
        st.subheader("➕ Agregar Cliente")
        nom_c = st.text_input("Nombre")
        tel_c = st.text_input("Teléfono / WhatsApp")
        ubi_c = st.text_input("Ubicación Principal")
        btn_c = st.form_submit_button("Guardar Cliente")
        
        if btn_c and nom_c:
            nuevo_id_c = len(df_clientes) + 1 if not df_clientes.empty else 1
            nueva_c = pd.DataFrame([{"id": nuevo_id_c, "nombre": nom_c, "telefono": tel_c, "ubicacion": ubi_c, "saldo_pendiente": 0.0}])
            df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
            if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                st.success("Cliente agregado exitosamente.")
                st.rerun()

    # --- SECCIÓN EDITAR CLIENTE ---
    if not df_clientes.empty:
        st.markdown("---")
        st.subheader("✏️ Editar Cliente Existente")
        opciones_clientes = {f"{row['nombre']} (ID: {row['id']})": row['id'] for _, row in df_clientes.iterrows()}
        
        # Selector con cuadro vacío por defecto
        cli_sel_label = st.selectbox(
            "Selecciona el cliente a editar",
            list(opciones_clientes.keys()),
            index=None,
            placeholder="Escribe o selecciona un cliente..."
        )
        
        # Solo muestra el formulario si hay un cliente seleccionado
        if cli_sel_label:
            id_cli_sel = opciones_clientes[cli_sel_label]
            datos_cli = df_clientes[df_clientes['id'] == id_cli_sel].iloc[0]
            
            with st.form("form_editar_cliente"):
                edit_nom_c = st.text_input("Nombre", value=str(datos_cli['nombre']))
                edit_tel_c = st.text_input("Teléfono / WhatsApp", value=str(datos_cli['telefono']) if pd.notna(datos_cli['telefono']) else "")
                edit_ubi_c = st.text_input("Ubicación Principal", value=str(datos_cli['ubicacion']) if pd.notna(datos_cli['ubicacion']) else "")
                
                if st.form_submit_button("Actualizar Cliente"):
                    idx = df_clientes[df_clientes['id'] == id_cli_sel].index[0]
                    
                    # Convertir columnas a tipo texto para evitar errores con signos o guiones
                    df_clientes['nombre'] = df_clientes['nombre'].astype(str)
                    df_clientes['telefono'] = df_clientes['telefono'].astype(str)
                    df_clientes['ubicacion'] = df_clientes['ubicacion'].astype(str)
                    
                    df_clientes.at[idx, 'nombre'] = edit_nom_c
                    df_clientes.at[idx, 'telefono'] = edit_tel_c
                    df_clientes.at[idx, 'ubicacion'] = edit_ubi_c

# --- MÓDULO 4: PERFILES MOTORIZADOS ---
elif opcion_menu == " Perfiles Motorizados":
    st.header("🏍️ Gestión de Motorizados")
    if not df_motos.empty:
        st.dataframe(df_motos, use_container_width=True)
        
    with st.form("form_agregar_moto", clear_on_submit=True):
        st.subheader("➕ Agregar Motorizado")
        nom_m = st.text_input("Nombre del Chofer")
        tel_m = st.text_input("Teléfono")
        com_m = st.number_input("% Ganancia Base", min_value=0.0, max_value=100.0, value=66.67)
        btn_m = st.form_submit_button("Guardar Motorizado")
        
        if btn_m and nom_m:
            nuevo_id_m = len(df_motos) + 1 if not df_motos.empty else 1
            nueva_m = pd.DataFrame([{"id": nuevo_id_m, "nombre": nom_m, "telefono": tel_m, "porcentaje_ganancia": com_m, "saldo_pendiente": 0.0}])
            df_motos = pd.concat([df_motos, nueva_m], ignore_index=True)
            if guardar_csv_en_github(FILE_MOTORIZADOS, df_motos, sha_motos, f"Nuevo motorizado {nom_m}"):
                st.success("Motorizado agregado exitosamente.")
                st.rerun()

    # --- SECCIÓN EDITAR MOTORIZADO (FUERA DEL FORMULARIO DE AGREGAR) ---
    if not df_motos.empty:
        st.markdown("---")
        st.subheader("✏️ Editar Motorizado Existente")
        
        opciones_motos = {f"{row['nombre']} (ID: {row['id']})": row['id'] for _, row in df_motos.iterrows()}
        moto_sel_label = st.selectbox("Selecciona el motorizado a editar", list(opciones_motos.keys()))
        id_moto_sel = opciones_motos[moto_sel_label]
        datos_moto = df_motos[df_motos['id'] == id_moto_sel].iloc[0]
        
        with st.form("form_editar_moto"):
            edit_nombre = st.text_input("Nombre del Chofer", value=str(datos_moto['nombre']))
            edit_tel = st.text_input("Teléfono", value=str(datos_moto['telefono']) if pd.notna(datos_moto['telefono']) else "")
            edit_pct = st.number_input("% Ganancia Base", value=float(datos_moto['porcentaje_ganancia']), step=0.1)
            
            if st.form_submit_button("Actualizar Motorizado"):
                idx = df_motos[df_motos['id'] == id_moto_sel].index[0]
                df_motos.at[idx, 'nombre'] = edit_nombre
                df_motos.at[idx, 'telefono'] = edit_tel
                df_motos.at[idx, 'porcentaje_ganancia'] = edit_pct
                if guardar_csv_en_github(FILE_MOTORIZADOS, df_motos, sha_motos, f"Editar motorizado {edit_nombre}"):
                    st.success(f"Motorizado {edit_nombre} actualizado exitosamente.")
                    st.rerun()
