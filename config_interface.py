
def f():
    import streamlit as st
    import os
    from configparser import ConfigParser
    import main

    PARENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILES_FOLDER = os.path.join(PARENT_FOLDER, "config_files")
    KEYS_FILES_FOLDER = os.path.join(CONFIG_FILES_FOLDER, "keys")

    def get_config(filename):
        config_path = os.path.join(CONFIG_FILES_FOLDER, filename)
        config = ConfigParser()
        config.read(config_path)
        return config, config_path

    def get_syncs():
        config_files = [filename for filename in os.listdir(CONFIG_FILES_FOLDER) if os.path.splitext(filename)[1] == ".ini"]
        syncs = []
        for filename in config_files:
            config, _ = get_config(filename)
            syncs.append( {"filename": filename, "config": config["security"]} )
        return syncs

    def create_sync():

        path_safe_name = st.session_state.name.replace(" ", "_").replace("/", "_").replace("\\", "_")

        # Salva arquivo de chaves Google
        key_file_name = f"google_keys_{path_safe_name}.json"
        key_file_path = os.path.join(KEYS_FILES_FOLDER, key_file_name)
        with open(key_file_path, "wb") as file:
            file.write(st.session_state.sa_keys.getvalue())
        
        # Escreve parâmetros de configuração
        config = ConfigParser()
        config['security'] = {
            "NAME": st.session_state.name,
            "CALENDAR_ID_EMAIL": st.session_state.calendar_id,
            "PROJECTS_API_KEY": st.session_state.op_api,
            "SHEET_ID": st.session_state.sheet_id,
            "CREDENTIALS_PATH": key_file_path
        }

        # Salva filtros de origem das tarefas
        if st.session_state.origin_type == "Atribuído":
            config['security']['ASSIGNEE_ID'] = st.session_state.origin_value
        elif st.session_state.origin_type == "Projetos":
            config['security']['PROJECT_NAME'] = st.session_state.origin_value
        
        # Salva config.ini
        with open(os.path.join(CONFIG_FILES_FOLDER, f"config_{path_safe_name}.ini"), "w") as file:
            config.write(file)

        st.rerun()

    def delete_sync(sync):
        filename = sync["filename"]
        config, config_path = get_config(filename)
        keys_path = config['security']['CREDENTIALS_PATH']
        
        os.remove(keys_path)
        os.remove(config_path)

    st.markdown("## Sincronizações OpenProject-Calendar")
    st.write("Sincroniza pacotes de trabalho do Open Projects com o Google Calendars.")

    # Lista salvas
    with st.expander("🔄 Sincronizações cadastradas"):

        syncs = get_syncs()
        for sync in syncs:
            filename = sync['filename']
            config = sync['config']
            
            name = config['name']

            if config.get('assignee_id', None):
                origin_type = "Atribuído"
                origin_value = config['assignee_id']
            elif config.get('project_name', None):
                origin_type = "Projetos"
                origin_value = config['project_name']

            button_key_sync_name = name.replace(" ", "_")

            # Nome
            st.markdown(f"#### {name}")
            # Origem das tarefas
            st.markdown(f"{origin_type}: {", ".join(origin_value.split(","))}")

            _, config_path = get_config(sync["filename"])

            cols = st.columns(2)
            with cols[0]:
                st.button("🔄 Sincronizar", on_click=lambda config_path=config_path: main.main(config_path), key=f"button_sync_{button_key_sync_name}")
            #with cols[1]:
            #    with open(config['CREDENTIALS_PATH'], "r") as f:
            #        st.download_button("📥 Baixar arquivo chaves", f, file_name="google_keys.json", key=f"button_download_keys_{button_key_sync_name}")
            #with cols[2]:
            #    with open(config_path, "r") as f:
            #        st.download_button("📥 Baixar configuração", f, file_name="config.ini", key=f"button_download_config_{button_key_sync_name}")
            with cols[1]:
                st.button(f"🗑️ Apagar sincronização", on_click=lambda sync=sync: delete_sync(sync), key=f"delete_button_{button_key_sync_name}")


    with st.expander("🆕 Criar nova sincronização"):
        with st.expander("Preparar acessos:"):
            st.markdown("""
                - Criar **service account** que será utilizada para manipular Calendar e Sheets:
                    1. Logado na conta que irá utilizar o Calendar, abrir o [Console do Google Cloud](https://console.cloud.google.com)
                    2. Criar projeto novo
                    3. [APIs](https://console.cloud.google.com/apis/) -> Biblioteca -> **Google Calendar API** -> Ativar
                    4. [APIs](https://console.cloud.google.com/apis/) -> Biblioteca -> **Google Sheet API** -> Ativar
                    5. Em IAM & Admin abrir Service Accounts e criar conta de serviço, com permissão de proprietário
                        - Abrir página da conta de serviço, clicando no link da coluna E-mail
                    6. Na aba Keys, criar uma chave JSON
                - Autorizar conta de serviço para acessar calendário:
                    1. Google Calendar -> Configurações -> Clicar no calendário que será utilizado
                    2. Em compartilhar com, dar permissão de edição para o e-mail da conta de serviço
                - Criar uma planilha nova no Google Sheet, que será utilizada de log:
                    1. Criar duas abas, com nomes `actions` e `errors`
                    2. Compartilhar com o e-mail da conta de serviço, como editor            
            """)

        with st.form('create_sync'):
            name = st.text_input("Nome da sincronização", key="name")
            origin_type = st.radio("Origem das tarefas", options=["Atribuído", "Projetos"], index=0, key="origin_type")
            origin_value = st.text_input("Valor da origem", key="origin_value", help="ID do atribuído, ou nome dos projetos, separado por vírgula.")

            calendar_id = st.text_input("ID do Calendário", key="calendar_id")
            op_api = st.text_input("API do OpenProjects", key="op_api")
            sheet_id = st.text_input("ID da planilha do Google Sheet", key="sheet_id")
            sa_keys = st.file_uploader(label="Arquivo JSON de chaves da conta de serviço do Google", key="sa_keys")

            submit = st.form_submit_button("Salvar")

            if submit:
                create_sync()