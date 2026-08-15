def verificar_acesso():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    
    # Se não for admin e não clicou em modo convidado, mostra a porta
    if not st.session_state.is_admin and not st.session_state.guest_mode:
        
        # Aumentamos um pouco a coluna central (2.5) para caber os itens lado a lado
        col1, col2, col3 = st.columns([1, 2.5, 1])
        
        with col2:
            with st.container(border=True):
                # 1. CABEÇALHO CENTRALIZADO
                col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
                with col_logo2:
                    if os.path.exists("logo.png"):
                        st.image("logo.png", use_container_width=True)
                
                st.markdown("<h2 style='text-align: center;'>⚡ Zeus AI</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #a0a0a0;'>Auditoria disciplinar e forense para eSports.</p>", unsafe_allow_html=True)
                
                st.divider()
                
                # 2. OPÇÕES LADO A LADO
                col_admin, col_guest = st.columns(2, gap="large")
                
                with col_admin:
                    st.markdown("### 🛡️ Equipe GC")
                    st.caption("Acesso irrestrito para operação.")
                    
                    senha_input = st.text_input("Chave corporativa:", type="password", placeholder="Insira a chave...", label_visibility="collapsed")
                    
                    if st.button("Entrar no Zeus", type="primary", use_container_width=True):
                        if senha_input == senha_correta:
                            st.session_state.is_admin = True
                            st.query_params["auth"] = senha_correta
                            st.rerun()
                        else:
                            st.error("Chave inválida.")
                
                with col_guest:
                    st.markdown("### 👤 Portfólio")
                    st.caption("Visitante? Teste a IA na prática.")
                    
                    # Espaçamento invisível para alinhar o botão do visitante com o botão do Admin
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button("Acessar Modo Convidado", use_container_width=True):
                        st.session_state.guest_mode = True
                        st.query_params["guest"] = "true"
                        st.rerun()
        
        # Interrompe a renderização do app aqui
        st.stop()