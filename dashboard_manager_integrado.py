#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Manager - Versão Integrada
Gerencia Dashboard Master com comunicação bidirecional com análises SPSS
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

class DashboardManagerIntegrated:
    def __init__(self, config_file="dashboard_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Carrega configuração existente ou cria uma nova"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Erro ao carregar config: {e}")
        
        return {
            "title": "Dashboard Master - Opinião Informação Estratégica",
            "created": datetime.now().isoformat(),
            "integration": {
                "communication": True,
                "filter_sync": True,
                "export_centralized": True
            },
            "items": [
                {
                    "id": "home",
                    "title": "Início", 
                    "icon": "🏠",
                    "type": "action",
                    "action": "showWelcome"
                }
            ]
        }
    
    def save_config(self):
        """Salva configuração no arquivo"""
        self.config["updated"] = datetime.now().isoformat()
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"✅ Configuração salva em {self.config_file}")
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
    
    def add_analysis(self, name: str, filename: str, group: str = None, icon: str = "📊", description: str = ""):
        """Adiciona nova análise ao menu"""
        item_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c')
        
        new_item = {
            "id": item_id,
            "title": name,
            "file": filename,
            "description": description,
            "added": datetime.now().isoformat(),
            "integrated": True  # Marca como integrado
        }
        
        if group:
            existing_group = None
            for item in self.config["items"]:
                if item.get("type") == "group" and item["title"] == group:
                    existing_group = item
                    break
            
            if not existing_group:
                group_id = group.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c')
                existing_group = {
                    "id": group_id,
                    "title": group,
                    "icon": "📁",
                    "type": "group", 
                    "expanded": False,
                    "children": []
                }
                self.config["items"].append(existing_group)
                print(f"📁 Novo grupo criado: {group}")
            
            existing_group["children"].append(new_item)
            print(f"✅ Análise '{name}' adicionada ao grupo '{group}'")
        
        else:
            new_item.update({
                "icon": icon,
                "type": "file"
            })
            self.config["items"].append(new_item)
            print(f"✅ Análise '{name}' adicionada como item individual")
        
        self.save_config()
    
    def generate_html_integrated(self, output_file="dashboard_master_integrated.html"):
        """Gera HTML do Dashboard Master com integração completa"""
        
        # Template HTML integrado
        html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary: #4A90E2;
            --primary-dark: #357ABD;
            --secondary: #1976D2;
            --bg: #f8f9fa;
            --sidebar-bg: #ffffff;
            --text: #333333;
            --text-light: #666666;
            --border: #e0e0e0;
            --hover: #f0f4f8;
            --active: #e5eef7;
            --success: #10b981;
            --warning: #f59e0b;
            --shadow: 0 2px 10px rgba(0,0,0,0.1);
            --shadow-lg: 0 4px 20px rgba(0,0,0,0.15);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            overflow: hidden;
        }}

        .dashboard-container {{
            display: flex;
            height: 100vh;
        }}

        .sidebar {{
            width: 300px;
            background: var(--sidebar-bg);
            border-right: 2px solid var(--border);
            box-shadow: var(--shadow-lg);
            display: flex;
            flex-direction: column;
            transition: width 0.3s ease;
            z-index: 1000;
        }}

        .sidebar.collapsed {{
            width: 70px;
        }}

        .sidebar-header {{
            padding: 20px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
        }}

        .sidebar.collapsed .sidebar-header {{
            padding: 15px 5px;
        }}

        .sidebar-header .logo-text {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .sidebar-header .logo-text {{
            font-size: 10px;
            line-height: 1.2;
        }}

        .sidebar-header .subtitle {{
            font-size: 12px;
            opacity: 0.9;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .sidebar-header .subtitle {{
            display: none;
        }}

        .sidebar-toggle {{
            position: absolute;
            top: 20px;
            right: -15px;
            width: 30px;
            height: 30px;
            background: var(--primary);
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            z-index: 1001;
        }}

        .sidebar-toggle:hover {{
            background: var(--primary-dark);
            transform: scale(1.1);
        }}

        .sidebar-menu {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }}

        .menu-item {{
            display: flex;
            align-items: center;
            padding: 12px 20px;
            color: var(--text);
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 4px solid transparent;
            position: relative;
        }}

        .menu-item:hover {{
            background: var(--hover);
            border-left-color: var(--primary);
        }}

        .menu-item.active {{
            background: var(--active);
            border-left-color: var(--secondary);
            color: var(--secondary);
            font-weight: 600;
        }}

        .menu-item .icon {{
            min-width: 24px;
            width: 24px;
            height: 24px;
            margin-right: 12px;
            font-size: 18px;
            text-align: center;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .menu-item .icon {{
            margin-right: 0;
        }}

        .menu-item .text {{
            flex: 1;
            transition: all 0.3s ease;
            white-space: nowrap;
        }}

        .sidebar.collapsed .menu-item .text {{
            display: none;
        }}

        .menu-item .expand-icon {{
            font-size: 12px;
            transform: rotate(0deg);
            transition: transform 0.3s ease;
        }}

        .menu-item.expanded .expand-icon {{
            transform: rotate(90deg);
        }}

        .sidebar.collapsed .menu-item .expand-icon {{
            display: none;
        }}

        .submenu {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
            background: #f8f9fa;
            border-left: 2px solid var(--primary);
        }}

        .submenu.expanded {{
            max-height: 500px;
        }}

        .submenu-item {{
            display: flex;
            align-items: center;
            padding: 10px 20px 10px 50px;
            color: var(--text-light);
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
            position: relative;
        }}

        .submenu-item:hover {{
            background: var(--hover);
            border-left-color: var(--primary);
            color: var(--text);
        }}

        .submenu-item.active {{
            background: var(--active);
            border-left-color: var(--secondary);
            color: var(--secondary);
            font-weight: 600;
        }}

        .submenu-item.integrated {{
            border-right: 3px solid var(--success);
        }}

        .sidebar.collapsed .submenu {{
            display: none;
        }}

        .tooltip {{
            position: absolute;
            left: 80px;
            top: 50%;
            transform: translateY(-50%);
            background: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            z-index: 1000;
        }}

        .sidebar.collapsed .menu-item:hover .tooltip {{
            opacity: 0.9;
        }}

        .main-content {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg);
        }}

        .main-header {{
            background: white;
            border-bottom: 1px solid var(--border);
            padding: 20px 30px;
            box-shadow: var(--shadow);
            z-index: 100;
        }}

        .main-header h1 {{
            font-size: 24px;
            color: var(--primary);
            margin-bottom: 5px;
        }}

        .main-header .subtitle {{
            color: var(--text-light);
            font-size: 14px;
        }}

        .breadcrumb {{
            display: flex;
            align-items: center;
            margin-top: 10px;
            font-size: 14px;
            color: var(--text-light);
        }}

        .breadcrumb-item {{
            color: var(--text-light);
        }}

        .breadcrumb-item.active {{
            color: var(--primary);
            font-weight: 600;
        }}

        .breadcrumb-separator {{
            margin: 0 8px;
            color: var(--border);
        }}

        /* ========= BARRA DE STATUS INTEGRADA ========= */
        .status-bar {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 8px 30px;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }}

        .status-info {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .status-actions {{
            display: flex;
            gap: 10px;
        }}

        .status-btn {{
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        .status-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .content-frame {{
            flex: 1;
            border: none;
            background: white;
            margin: 20px;
            border-radius: 12px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }}

        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            font-size: 18px;
            color: var(--text-light);
        }}

        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid var(--border);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 15px;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        .welcome {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            padding: 40px;
        }}

        .welcome-icon {{
            font-size: 64px;
            color: var(--primary);
            margin-bottom: 20px;
        }}

        .welcome h2 {{
            color: var(--primary);
            margin-bottom: 10px;
        }}

        .welcome p {{
            color: var(--text-light);
            margin-bottom: 30px;
            max-width: 500px;
            line-height: 1.6;
        }}

        .integration-status {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            color: #059669;
        }}

        .integration-status h3 {{
            margin-bottom: 10px;
            color: var(--success);
        }}

        @media (max-width: 768px) {{
            .sidebar {{
                position: absolute;
                left: -300px;
                width: 300px;
                z-index: 1000;
                transition: left 0.3s ease;
            }}

            .sidebar.mobile-open {{
                left: 0;
            }}

            .sidebar.collapsed {{
                left: -300px;
            }}

            .main-content {{
                margin-left: 0;
            }}

            .sidebar-toggle {{
                position: fixed;
                top: 20px;
                left: 20px;
                right: auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo-text">Dashboard Master</div>
                <div class="subtitle">Integrado</div>
            </div>

            <button class="sidebar-toggle" id="sidebarToggle" onclick="toggleSidebar()">⟵</button>

            <nav class="sidebar-menu" id="sidebarMenu">
                <!-- Menu será gerado pelo JavaScript -->
            </nav>
        </div>

        <div class="main-content">
            <!-- Barra de Status -->
            <div class="status-bar" id="statusBar">
                <div class="status-info">
                    <span id="statusText">🏠 Página inicial</span>
                </div>
                <div class="status-actions">
                    <button class="status-btn" onclick="clearAllFiltersGlobal()">🔄 Limpar Filtros</button>
                    <button class="status-btn" onclick="exportCurrentAnalysis()">📊 Exportar</button>
                </div>
            </div>

            <header class="main-header">
                <h1 id="mainTitle">Dashboard Master Integrado</h1>
                <p class="subtitle" id="mainSubtitle">Sistema integrado de análises SPSS</p>
                <nav class="breadcrumb" id="breadcrumb">
                    <span class="breadcrumb-item active">Início</span>
                </nav>
            </header>

            <iframe class="content-frame" id="contentFrame" style="display: none;"></iframe>
            
            <div class="welcome" id="welcomeState">
                <div class="welcome-icon">📊</div>
                <h2>Dashboard Master Integrado</h2>
                <p>Sistema avançado com comunicação bidirecional entre análises SPSS e interface master.</p>
                
                <div class="integration-status">
                    <h3>🔗 Funcionalidades Integradas</h3>
                    <ul style="text-align: left; line-height: 1.8;">
                        <li>✅ Comunicação em tempo real com análises</li>
                        <li>✅ Sincronização de filtros</li>
                        <li>✅ Exportação centralizada</li>
                        <li>✅ Status de carregamento</li>
                        <li>✅ Controles globais</li>
                    </ul>
                </div>

                <div style="background: var(--hover); padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="color: var(--primary); margin-bottom: 10px;">Como usar:</h3>
                    <ol style="text-align: left; color: var(--text); line-height: 1.8;">
                        <li>Use o <code>criar_dashboard_integrado.py</code> para gerar análises</li>
                        <li>Configure o menu usando <code>dashboard_manager.py</code></li>
                        <li>Navegue entre análises - filtros se sincronizam</li>
                        <li>Use controles globais na barra de status</li>
                    </ol>
                </div>
            </div>

            <div class="loading" id="loadingState" style="display: none;">
                <div class="loading-spinner"></div>
                Carregando análise integrada...
            </div>
        </div>
    </div>

    <script>
        const menuConfig = {menu_config_json};
        let currentSidebarState = 'expanded';
        let currentMenuItem = null;
        let currentAnalysisFrame = null;

        // ========= COMUNICAÇÃO COM ANÁLISES =========
        let analysisStats = {{
            loaded: 0,
            variables: 0,
            filters: 0,
            records: 0,
            selections: 0
        }};

        function updateStatusBar(text) {{
            document.getElementById('statusText').textContent = text;
        }}

        function clearAllFiltersGlobal() {{
            if (currentAnalysisFrame) {{
                currentAnalysisFrame.postMessage({{
                    source: 'dashboard-master',
                    type: 'clear-all-filters'
                }}, '*');
                updateStatusBar('🔄 Filtros limpos globalmente');
            }}
        }}

        function exportCurrentAnalysis() {{
            if (currentAnalysisFrame) {{
                currentAnalysisFrame.postMessage({{
                    source: 'dashboard-master', 
                    type: 'export-data'
                }}, '*');
                updateStatusBar('📊 Exportação solicitada');
            }}
        }}

        // Escuta mensagens das análises
        window.addEventListener('message', (event) => {{
            if (event.data && event.data.source === 'spss-analysis') {{
                const {{ type, data, filename }} = event.data;
                
                switch (type) {{
                    case 'analysis-loaded':
                        analysisStats = {{
                            loaded: 1,
                            variables: data.variables,
                            filters: data.filters, 
                            records: data.records,
                            selections: 0
                        }};
                        updateStatusBar(`📈 ${{data.variables}} variáveis, ${{data.filters}} filtros, ${{data.records}} registros`);
                        break;
                        
                    case 'filter-changed':
                        updateStatusBar(`🔍 Filtro alterado: ${{data.filterTitle}}`);
                        break;
                        
                    case 'selection-changed':
                        analysisStats.selections = data.totalSelections;
                        updateStatusBar(`🎯 ${{data.totalSelections}} seleções ativas`);
                        break;
                        
                    case 'selections-cleared':
                        analysisStats.selections = 0;
                        updateStatusBar('🔄 Seleções limpas');
                        break;
                        
                    case 'filters-cleared':
                        updateStatusBar('🔄 Filtros limpos');
                        break;
                        
                    case 'data-exported':
                        updateStatusBar(`📊 Dados exportados: ${{data.filename}}`);
                        break;
                }}
            }}
        }});

        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('sidebarToggle');
            
            if (currentSidebarState === 'expanded') {{
                sidebar.classList.add('collapsed');
                toggleBtn.innerHTML = '⟶';
                currentSidebarState = 'collapsed';
            }} else {{
                sidebar.classList.remove('collapsed');
                toggleBtn.innerHTML = '⟵';
                currentSidebarState = 'expanded';
            }}
        }}

        function renderMenu() {{
            const menuContainer = document.getElementById('sidebarMenu');
            menuContainer.innerHTML = '';

            menuConfig.items.forEach(item => {{
                if (item.type === 'group') {{
                    renderMenuGroup(menuContainer, item);
                }} else {{
                    renderMenuItem(menuContainer, item);
                }}
            }});
        }}

        function renderMenuGroup(container, group) {{
            const groupItem = document.createElement('div');
            groupItem.className = `menu-item ${{group.expanded ? 'expanded' : ''}}`;
            groupItem.innerHTML = `
                <span class="icon">${{group.icon}}</span>
                <span class="text">${{group.title}}</span>
                <span class="expand-icon">▶</span>
                <div class="tooltip">${{group.title}}</div>
            `;

            groupItem.addEventListener('click', () => {{
                group.expanded = !group.expanded;
                groupItem.classList.toggle('expanded', group.expanded);
                submenu.classList.toggle('expanded', group.expanded);
            }});

            container.appendChild(groupItem);

            const submenu = document.createElement('div');
            submenu.className = `submenu ${{group.expanded ? 'expanded' : ''}}`;

            group.children.forEach(child => {{
                const submenuItem = document.createElement('div');
                submenuItem.className = `submenu-item ${{child.integrated ? 'integrated' : ''}}`;
                submenuItem.innerHTML = `<span class="text">${{child.title}}</span>`;

                submenuItem.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    loadContent(child);
                    updateActiveState(submenuItem);
                    updateBreadcrumb([group.title, child.title]);
                }});

                submenu.appendChild(submenuItem);
            }});

            container.appendChild(submenu);
        }}

        function renderMenuItem(container, item) {{
            const menuItem = document.createElement('div');
            menuItem.className = 'menu-item';
            menuItem.innerHTML = `
                <span class="icon">${{item.icon}}</span>
                <span class="text">${{item.title}}</span>
                <div class="tooltip">${{item.title}}</div>
            `;

            menuItem.addEventListener('click', () => {{
                if (item.type === 'action') {{
                    if (item.action === 'showWelcome') {{
                        showWelcome();
                    }}
                }} else if (item.type === 'file') {{
                    loadContent(item);
                }}
                updateActiveState(menuItem);
                updateBreadcrumb([item.title]);
            }});

            container.appendChild(menuItem);
        }}

        function loadContent(item) {{
            const frame = document.getElementById('contentFrame');
            const welcome = document.getElementById('welcomeState');
            const loading = document.getElementById('loadingState');
            const title = document.getElementById('mainTitle');
            const subtitle = document.getElementById('mainSubtitle');

            welcome.style.display = 'none';
            frame.style.display = 'none';
            loading.style.display = 'flex';

            title.textContent = item.title;
            subtitle.textContent = `Carregando ${{item.file}}...`;
            updateStatusBar('⏳ Carregando análise...');

            setTimeout(() => {{
                frame.src = item.file;
                currentAnalysisFrame = frame.contentWindow;
                
                frame.onload = () => {{
                    loading.style.display = 'none';
                    frame.style.display = 'block';
                    subtitle.textContent = `Análise: ${{item.file}}`;
                    updateStatusBar(`✅ ${{item.title}} carregado`);
                }};

                frame.onerror = () => {{
                    loading.style.display = 'none';
                    welcome.style.display = 'flex';
                    welcome.innerHTML = `
                        <div class="welcome-icon" style="color: #ef4444;">❌</div>
                        <h2 style="color: #ef4444;">Arquivo não encontrado</h2>
                        <p>O arquivo "${{item.file}}" não foi encontrado.</p>
                        <div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; color: #92400e;">
                            <strong>💡 Dica:</strong> Use o <code>criar_dashboard_integrado.py</code> 
                            para gerar análises compatíveis com este sistema.
                        </div>
                    `;
                    subtitle.textContent = `Erro: ${{item.file}}`;
                    updateStatusBar('❌ Arquivo não encontrado');
                }};
            }}, 500);
        }}

        function showWelcome() {{
            const frame = document.getElementById('contentFrame');
            const welcome = document.getElementById('welcomeState');
            const loading = document.getElementById('loadingState');
            const title = document.getElementById('mainTitle');
            const subtitle = document.getElementById('mainSubtitle');

            frame.style.display = 'none';
            loading.style.display = 'none';
            welcome.style.display = 'flex';

            title.textContent = 'Dashboard Master Integrado';
            subtitle.textContent = 'Sistema integrado de análises SPSS';
            updateStatusBar('🏠 Página inicial');
            currentAnalysisFrame = null;
        }}

        function updateActiveState(activeElement) {{
            document.querySelectorAll('.menu-item.active, .submenu-item.active').forEach(el => {{
                el.classList.remove('active');
            }});
            activeElement.classList.add('active');
            currentMenuItem = activeElement;
        }}

        function updateBreadcrumb(path) {{
            const breadcrumb = document.getElementById('breadcrumb');
            breadcrumb.innerHTML = path.map((item, index) => {{
                const isLast = index === path.length - 1;
                return `
                    <span class="breadcrumb-item ${{isLast ? 'active' : ''}}">${{item}}</span>
                    ${{!isLast ? '<span class="breadcrumb-separator">›</span>' : ''}}
                `;
            }}).join('');
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            renderMenu();
            showWelcome();
            updateBreadcrumb(['Início']);
            
            const homeItem = document.querySelector('.menu-item');
            if (homeItem) {{
                homeItem.classList.add('active');
            }}
            
            console.log('🔗 Dashboard Master Integrado carregado!');
        }});

        window.addEventListener('resize', () => {{
            if (window.innerWidth <= 768) {{
                if (currentSidebarState === 'expanded') {{
                    document.getElementById('sidebar').classList.add('mobile-open');
                }}
            }} else {{
                document.getElementById('sidebar').classList.remove('mobile-open');
            }}
        }});
    </script>
</body>
</html>"""

        # Calcula estatísticas
        total_groups = len([item for item in self.config["items"] if item.get("type") == "group"])
        total_files = len([item for item in self.config["items"] if item.get("type") == "file"])
        total_subitems = sum(len(item.get("children", [])) for item in self.config["items"] if item.get("type") == "group")
        total_integrated = 0
        
        # Conta itens integrados
        for item in self.config["items"]:
            if item.get("type") == "file" and item.get("integrated"):
                total_integrated += 1
            elif item.get("type") == "group":
                for child in item.get("children", []):
                    if child.get("integrated"):
                        total_integrated += 1
        
        stats_text = f"{total_groups} grupos, {total_files} análises individuais, {total_subitems} subitens, {total_integrated} integradas"
        
        # Gera HTML
        html_content = html_template.format(
            title=self.config["title"],
            generated_at=datetime.now().strftime("%d/%m/%Y às %H:%M"),
            stats_text=stats_text,
            menu_config_json=json.dumps(self.config, ensure_ascii=False)
        )
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ Dashboard Master Integrado gerado: {output_file}")
            print(f"🔗 Funcionalidades integradas:")
            print(f"   • Comunicação bidirecional")
            print(f"   • Sincronização de filtros")
            print(f"   • Status em tempo real")
            print(f"   • Controles globais")
        except Exception as e:
            print(f"❌ Erro ao gerar HTML: {e}")

def main():
    print("🚀 GERENCIADOR DO DASHBOARD MASTER INTEGRADO")
    print("=" * 50)
    
    manager = DashboardManagerIntegrated()
    
    while True:
        print(f"\n📋 MENU:")
        print("1. ➕ Adicionar análise integrada")
        print("2. 📁 Criar grupo")
        print("3. 📋 Listar itens")
        print("4. 🗑️  Remover item")
        print("5. 🌐 Gerar HTML integrado")
        print("6. 📤 Exportar configuração")
        print("7. 📥 Importar configuração") 
        print("8. 🔗 Verificar integração")
        print("9. ❌ Sair")
        
        choice = input("\n👉 Escolha uma opção: ").strip()
        
        if choice == "1":
            print("\n➕ ADICIONAR ANÁLISE INTEGRADA")
            name = input("Nome da análise: ").strip()
            if not name:
                print("❌ Nome é obrigatório")
                continue
            
            filename = input("Nome do arquivo HTML (gerado com criar_dashboard_integrado.py): ").strip()
            if not filename:
                print("❌ Nome do arquivo é obrigatório")
                continue
            
            if not filename.endswith('.html'):
                filename += '.html'
            
            group = input("Grupo (deixe vazio para item individual): ").strip() or None
            icon = input("Ícone (emoji, deixe vazio para 📊): ").strip() or "📊"
            description = input("Descrição (opcional): ").strip()
            
            manager.add_analysis(name, filename, group, icon, description)
        
        elif choice == "2":
            print("\n📁 CRIAR GRUPO")
            name = input("Nome do grupo: ").strip()
            if not name:
                print("❌ Nome é obrigatório")
                continue
            
            icon = input("Ícone (emoji, deixe vazio para 📁): ").strip() or "📁"
            
            group_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c')
            new_group = {
                "id": group_id,
                "title": name,
                "icon": icon,
                "type": "group",
                "expanded": False,
                "children": []
            }
            
            manager.config["items"].append(new_group)
            manager.save_config()
            print(f"📁 Grupo '{name}' criado")
        
        elif choice == "3":
            print("\n📋 ESTRUTURA DO MENU:")
            print("=" * 50)
            
            for item in manager.config["items"]:
                if item.get("type") == "group":
                    print(f"\n📁 {item['icon']} {item['title']} (ID: {item['id']})")
                    if "children" in item:
                        for child in item["children"]:
                            integrated_mark = " 🔗" if child.get("integrated") else ""
                            print(f"   └── 📊 {child['title']} → {child.get('file', 'N/A')}{integrated_mark} (ID: {child['id']})")
                    else:
                        print("   └── (vazio)")
                else:
                    icon = item.get('icon', '📄')
                    integrated_mark = " 🔗" if item.get("integrated") else ""
                    file_info = f" → {item.get('file', 'N/A')}" if item.get('file') else ""
                    print(f"{icon} {item['title']}{file_info}{integrated_mark} (ID: {item['id']})")
        
        elif choice == "4":
            print("\n🗑️  REMOVER ITEM")
            print("Listar itens primeiro para ver IDs...")
            continue
        
        elif choice == "5":
            print("\n🌐 GERAR HTML INTEGRADO")
            output_name = input("Nome do arquivo (deixe vazio para 'dashboard_master_integrated.html'): ").strip()
            if not output_name:
                output_name = "dashboard_master_integrated.html"
            
            if not output_name.endswith('.html'):
                output_name += '.html'
                
            manager.generate_html_integrated(output_name)
        
        elif choice == "6":
            print("\n📤 EXPORTAR CONFIGURAÇÃO")
            export_name = "dashboard_config_integrated.json"
            
            try:
                with open(export_name, 'w', encoding='utf-8') as f:
                    json.dump(manager.config, f, ensure_ascii=False, indent=2)
                print(f"✅ Configuração exportada para {export_name}")
            except Exception as e:
                print(f"❌ Erro na exportação: {e}")
        
        elif choice == "7":
            print("\n📥 IMPORTAR CONFIGURAÇÃO")
            import_name = input("Nome do arquivo JSON para importar: ").strip()
            
            if os.path.exists(import_name):
                try:
                    with open(import_name, 'r', encoding='utf-8') as f:
                        manager.config = json.load(f)
                    manager.save_config()
                    print(f"✅ Configuração importada de {import_name}")
                except Exception as e:
                    print(f"❌ Erro na importação: {e}")
            else:
                print(f"❌ Arquivo {import_name} não encontrado")
        
        elif choice == "8":
            print("\n🔗 VERIFICAÇÃO DE INTEGRAÇÃO")
            print("=" * 40)
            
            total_items = 0
            integrated_items = 0
            
            for item in manager.config["items"]:
                if item.get("type") == "file":
                    total_items += 1
                    if item.get("integrated"):
                        integrated_items += 1
                elif item.get("type") == "group":
                    for child in item.get("children", []):
                        total_items += 1
                        if child.get("integrated"):
                            integrated_items += 1
            
            print(f"📊 Total de análises: {total_items}")
            print(f"🔗 Análises integradas: {integrated_items}")
            print(f"📱 Taxa de integração: {(integrated_items/total_items*100):.1f}%" if total_items > 0 else "0%")
            
            if integrated_items < total_items:
                print(f"\n💡 Para integrar análises existentes:")
                print(f"   1. Regenere com criar_dashboard_integrado.py")
                print(f"   2. Substitua os arquivos antigos")
                print(f"   3. Recarregue o Dashboard Master")
        
        elif choice == "9":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
