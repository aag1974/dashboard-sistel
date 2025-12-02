#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Manager - Versão Header Overlay
Sistema otimizado onde análises SPSS sobrepõem header e Dashboard Master só fornece sidebar
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

class DashboardManagerOverlay:
    def __init__(self, config_file="dashboard_overlay_config.json"):
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
            "title": "Dashboard Master - Header Overlay",
            "created": datetime.now().isoformat(),
            "architecture": "header_overlay",
            "description": "Sistema onde header SPSS sobrepõe interface e sidebar navega",
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
            print(f"✅ Configuração header overlay salva em {self.config_file}")
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
    
    def add_overlay_analysis(self, name: str, filename: str, group: str = None, icon: str = "🎯", description: str = ""):
        """Adiciona nova análise com header overlay ao menu"""
        item_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c')
        
        new_item = {
            "id": item_id,
            "title": name,
            "file": filename,
            "description": description,
            "overlay": True,
            "added": datetime.now().isoformat()
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
            print(f"✅ Análise overlay '{name}' adicionada ao grupo '{group}'")
        
        else:
            new_item.update({
                "icon": icon,
                "type": "file"
            })
            self.config["items"].append(new_item)
            print(f"✅ Análise overlay '{name}' adicionada como item individual")
        
        self.save_config()
    
    def create_group(self, name: str, icon: str = "📁"):
        """Cria um novo grupo vazio"""
        group_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c')
        
        new_group = {
            "id": group_id,
            "title": name,
            "icon": icon,
            "type": "group",
            "expanded": False,
            "children": []
        }
        
        self.config["items"].append(new_group)
        print(f"📁 Grupo '{name}' criado")
        self.save_config()
    
    def remove_item(self, item_id: str):
        """Remove um item ou grupo"""
        # Procura em itens principais
        for i, item in enumerate(self.config["items"]):
            if item["id"] == item_id:
                del self.config["items"][i]
                print(f"🗑️  Item '{item['title']}' removido")
                self.save_config()
                return True
        
        # Procura em subitens dos grupos
        for group in self.config["items"]:
            if group.get("type") == "group" and "children" in group:
                for i, child in enumerate(group["children"]):
                    if child["id"] == item_id:
                        del group["children"][i]
                        print(f"🗑️  Item '{child['title']}' removido do grupo '{group['title']}'")
                        self.save_config()
                        return True
        
        print(f"❌ Item '{item_id}' não encontrado")
        return False
    
    def list_items(self):
        """Lista todos os itens do menu"""
        print("\n📋 ESTRUTURA DO MENU HEADER OVERLAY:")
        print("=" * 50)
        
        for item in self.config["items"]:
            if item.get("type") == "group":
                print(f"\n📁 {item['icon']} {item['title']} (ID: {item['id']})")
                if "children" in item:
                    for child in item["children"]:
                        overlay_mark = " 🎯" if child.get("overlay") else ""
                        print(f"   └── 📊 {child['title']} → {child.get('file', 'N/A')}{overlay_mark} (ID: {child['id']})")
                else:
                    print("   └── (vazio)")
            else:
                icon = item.get('icon', '📄')
                overlay_mark = " 🎯" if item.get("overlay") else ""
                file_info = f" → {item.get('file', 'N/A')}" if item.get('file') else ""
                print(f"{icon} {item['title']}{file_info}{overlay_mark} (ID: {item['id']})")
    
    def generate_dashboard_overlay(self, output_file="dashboard_master_header_overlay_generated.html"):
        """Gera o Dashboard Master com arquitetura header overlay"""
        
        # Template HTML otimizado para header overlay
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
            height: 100vh;
        }}

        .dashboard-container {{
            display: flex;
            height: 100vh;
        }}

        .sidebar {{
            width: 280px;
            background: var(--sidebar-bg);
            border-right: 2px solid var(--border);
            box-shadow: var(--shadow-lg);
            display: flex;
            flex-direction: column;
            transition: width 0.3s ease;
            z-index: 1000;
            position: relative;
        }}

        .sidebar.collapsed {{
            width: 60px;
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
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 5px;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .sidebar-header .logo-text {{
            font-size: 8px;
            line-height: 1.1;
        }}

        .sidebar-header .subtitle {{
            font-size: 11px;
            opacity: 0.9;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .sidebar-header .subtitle {{
            display: none;
        }}

        .sidebar-toggle {{
            position: absolute;
            top: 20px;
            right: -12px;
            width: 24px;
            height: 24px;
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
            font-size: 12px;
        }}

        .sidebar-toggle:hover {{
            background: var(--primary-dark);
            transform: scale(1.1);
        }}

        .sidebar-menu {{
            flex: 1;
            overflow-y: auto;
            padding: 8px 0;
        }}

        .menu-item {{
            display: flex;
            align-items: center;
            padding: 10px 15px;
            color: var(--text);
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
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
            min-width: 20px;
            width: 20px;
            height: 20px;
            margin-right: 10px;
            font-size: 16px;
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
            font-size: 14px;
        }}

        .sidebar.collapsed .menu-item .text {{
            display: none;
        }}

        .menu-item .expand-icon {{
            font-size: 10px;
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
            background: rgba(74, 144, 226, 0.02);
            border-left: 2px solid var(--primary);
        }}

        .submenu.expanded {{
            max-height: 400px;
        }}

        .submenu-item {{
            display: flex;
            align-items: center;
            padding: 8px 15px 8px 40px;
            color: var(--text-light);
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 2px solid transparent;
            position: relative;
            font-size: 13px;
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

        .submenu-item.overlay-enabled {{
            border-right: 2px solid var(--success);
        }}

        .sidebar.collapsed .submenu {{
            display: none;
        }}

        .tooltip {{
            position: absolute;
            left: 70px;
            top: 50%;
            transform: translateY(-50%);
            background: #333;
            color: white;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 11px;
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
            background: var(--bg);
            position: relative;
            overflow: hidden;
        }}

        .content-frame {{
            width: 100%;
            height: 100vh;
            border: none;
            background: white;
        }}

        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-size: 18px;
            color: var(--text-light);
            background: white;
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
            height: 100vh;
            text-align: center;
            padding: 40px;
            background: white;
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

        .feature-highlight {{
            background: rgba(74, 144, 226, 0.05);
            border: 1px solid rgba(74, 144, 226, 0.2);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            color: var(--primary-dark);
        }}

        .feature-highlight h3 {{
            margin-bottom: 10px;
            color: var(--primary);
        }}

        @media (max-width: 768px) {{
            .sidebar {{
                position: absolute;
                left: -280px;
                width: 280px;
                z-index: 2000;
                transition: left 0.3s ease;
            }}

            .sidebar.mobile-open {{
                left: 0;
            }}

            .sidebar.collapsed {{
                left: -280px;
            }}

            .sidebar-toggle {{
                position: fixed;
                top: 15px;
                left: 15px;
                z-index: 3000;
            }}

            .main-content {{
                margin-left: 0;
            }}
        }}

        .mobile-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1500;
            display: none;
        }}

        .mobile-overlay.active {{
            display: block;
        }}

        .sidebar-footer {{
            padding: 10px 15px;
            border-top: 1px solid var(--border);
            background: var(--hover);
            font-size: 11px;
            color: var(--text-light);
            text-align: center;
        }}

        .sidebar.collapsed .sidebar-footer {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo-text">Dashboard Master</div>
                <div class="subtitle">Header Overlay</div>
            </div>

            <button class="sidebar-toggle" id="sidebarToggle" onclick="toggleSidebar()">⟵</button>

            <nav class="sidebar-menu" id="sidebarMenu">
                <!-- Menu será gerado dinamicamente -->
            </nav>

            <div class="sidebar-footer">
                <div>📊 {stats_text}</div>
                <div style="margin-top: 4px;">Gerado: {generated_at}</div>
            </div>
        </div>

        <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobileSidebar()"></div>

        <div class="main-content">
            <iframe class="content-frame" id="contentFrame" style="display: none;"></iframe>
            
            <div class="welcome" id="welcomeState">
                <div class="welcome-icon">🎯</div>
                <h2>Dashboard Master - Header Overlay</h2>
                <p>Sistema otimizado onde análises SPSS sobrepõem toda a interface com header próprio, mantendo apenas sidebar para navegação.</p>
                
                <div class="feature-highlight">
                    <h3>🚀 Arquitetura Header Overlay</h3>
                    <ul style="text-align: left; line-height: 1.8;">
                        <li>✅ <strong>Header SPSS fixo</strong> sobrepõe toda a tela</li>
                        <li>✅ <strong>Filtros compactos</strong> em linha única no header</li>
                        <li>✅ <strong>Máximo aproveitamento</strong> de espaço vertical</li>
                        <li>✅ <strong>Menu lateral mínimo</strong> sempre acessível</li>
                        <li>✅ <strong>Comunicação integrada</strong> via postMessage</li>
                    </ul>
                </div>

                <div style="background: var(--hover); padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="color: var(--primary); margin-bottom: 10px;">Como usar:</h3>
                    <ol style="text-align: left; color: var(--text); line-height: 1.8;">
                        <li>Gere análises com <code>criar_dashboard_header_overlay.py</code></li>
                        <li>Adicione no menu usando este gerenciador</li>
                        <li>Navegue - cada análise ocupa toda a tela</li>
                        <li>Use sidebar para trocar entre análises</li>
                    </ol>
                </div>
            </div>

            <div class="loading" id="loadingState" style="display: none;">
                <div class="loading-spinner"></div>
                Carregando análise com header overlay...
            </div>
        </div>
    </div>

    <script>
        const menuConfig = {menu_config_json};
        let currentSidebarState = 'expanded';
        let currentMenuItem = null;
        let currentAnalysisFrame = null;
        let isMobile = window.innerWidth <= 768;

        let analysisStats = {{
            loaded: 0,
            variables: 0,
            filters: 0,
            records: 0
        }};

        window.addEventListener('message', (event) => {{
            if (event.data && event.data.source === 'spss-analysis-overlay') {{
                const {{ type, data }} = event.data;
                
                switch (type) {{
                    case 'analysis-loaded':
                        analysisStats = {{
                            loaded: 1,
                            variables: data.variables,
                            filters: data.filters,
                            records: data.records
                        }};
                        console.log(`📊 Análise carregada: ${{data.variables}} vars, ${{data.filters}} filtros, ${{data.records}} registros`);
                        break;
                        
                    case 'status-update':
                        console.log(`📈 Status: ${{data.text}} (${{data.type}})`);
                        break;
                        
                    case 'filter-changed':
                        console.log(`🔍 Filtro: ${{data.filterTitle}} = ${{data.selected || 'Todos'}}`);
                        break;
                        
                    case 'selection-changed':
                        console.log(`🎯 Seleções: ${{data.totalSelections}} ativas`);
                        break;
                }}
            }}
        }});

        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('sidebarToggle');
            
            if (isMobile) {{
                sidebar.classList.toggle('mobile-open');
                document.getElementById('mobileOverlay').classList.toggle('active');
            }} else {{
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
        }}

        function closeMobileSidebar() {{
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('mobileOverlay');
            
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
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
                submenuItem.className = `submenu-item ${{child.overlay ? 'overlay-enabled' : ''}}`;
                submenuItem.innerHTML = `<span class="text">${{child.title}}</span>`;

                submenuItem.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    loadContent(child);
                    updateActiveState(submenuItem);
                    
                    if (isMobile) {{
                        closeMobileSidebar();
                    }}
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
                
                if (isMobile) {{
                    closeMobileSidebar();
                }}
            }});

            container.appendChild(menuItem);
        }}

        function loadContent(item) {{
            const frame = document.getElementById('contentFrame');
            const welcome = document.getElementById('welcomeState');
            const loading = document.getElementById('loadingState');

            welcome.style.display = 'none';
            frame.style.display = 'none';
            loading.style.display = 'flex';

            setTimeout(() => {{
                frame.src = item.file;
                currentAnalysisFrame = frame.contentWindow;
                
                frame.onload = () => {{
                    loading.style.display = 'none';
                    frame.style.display = 'block';
                    console.log(`✅ ${{item.title}} carregado com header overlay`);
                }};

                frame.onerror = () => {{
                    loading.style.display = 'none';
                    welcome.style.display = 'flex';
                    welcome.innerHTML = `
                        <div class="welcome-icon" style="color: #ef4444;">❌</div>
                        <h2 style="color: #ef4444;">Arquivo não encontrado</h2>
                        <p>O arquivo "${{item.file}}" não foi encontrado.</p>
                        <div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; color: #92400e;">
                            <strong>💡 Dica:</strong> Use o <code>criar_dashboard_header_overlay.py</code> 
                            para gerar análises compatíveis.
                        </div>
                    `;
                }};
            }}, 300);
        }}

        function showWelcome() {{
            const frame = document.getElementById('contentFrame');
            const welcome = document.getElementById('welcomeState');
            const loading = document.getElementById('loadingState');

            frame.style.display = 'none';
            loading.style.display = 'none';
            welcome.style.display = 'flex';
            currentAnalysisFrame = null;
        }}

        function updateActiveState(activeElement) {{
            document.querySelectorAll('.menu-item.active, .submenu-item.active').forEach(el => {{
                el.classList.remove('active');
            }});
            activeElement.classList.add('active');
            currentMenuItem = activeElement;
        }}

        function handleResize() {{
            const newIsMobile = window.innerWidth <= 768;
            
            if (newIsMobile !== isMobile) {{
                isMobile = newIsMobile;
                
                const sidebar = document.getElementById('sidebar');
                const overlay = document.getElementById('mobileOverlay');
                
                if (isMobile) {{
                    sidebar.classList.remove('collapsed');
                    sidebar.classList.remove('mobile-open');
                    overlay.classList.remove('active');
                }} else {{
                    sidebar.classList.remove('mobile-open');
                    overlay.classList.remove('active');
                    if (currentSidebarState === 'collapsed') {{
                        sidebar.classList.add('collapsed');
                    }}
                }}
            }}
        }}

        window.addEventListener('resize', handleResize);

        document.addEventListener('DOMContentLoaded', () => {{
            renderMenu();
            showWelcome();
            
            const homeItem = document.querySelector('.menu-item');
            if (homeItem) {{
                homeItem.classList.add('active');
            }}
            
            console.log('🎯 Dashboard Master - Header Overlay carregado!');
        }});

        function sendCommandToAnalysis(command, data = {{}}) {{
            if (currentAnalysisFrame) {{
                currentAnalysisFrame.postMessage({{
                    source: 'dashboard-master',
                    type: command,
                    data: data
                }}, '*');
            }}
        }}

        window.dashboardDebug = {{
            stats: () => analysisStats,
            sendCommand: sendCommandToAnalysis,
            toggleSidebar: toggleSidebar,
            showWelcome: showWelcome
        }};
    </script>
</body>
</html>"""

        # Calcula estatísticas
        total_groups = len([item for item in self.config["items"] if item.get("type") == "group"])
        total_files = len([item for item in self.config["items"] if item.get("type") == "file"])
        total_subitems = sum(len(item.get("children", [])) for item in self.config["items"] if item.get("type") == "group")
        total_overlay = 0
        
        # Conta itens com header overlay
        for item in self.config["items"]:
            if item.get("type") == "file" and item.get("overlay"):
                total_overlay += 1
            elif item.get("type") == "group":
                for child in item.get("children", []):
                    if child.get("overlay"):
                        total_overlay += 1
        
        stats_text = f"{total_groups} grupos • {total_files} individuais • {total_subitems} subitens • {total_overlay} overlay"
        
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
            print(f"✅ Dashboard Master Header Overlay gerado: {output_file}")
            print(f"🎯 Funcionalidades:")
            print(f"   • Header SPSS sobrepõe toda a interface")
            print(f"   • Sidebar mínima para navegação")
            print(f"   • Máximo aproveitamento de espaço")
            print(f"   • {total_overlay} análises com overlay configuradas")
        except Exception as e:
            print(f"❌ Erro ao gerar HTML: {e}")

def main():
    print("🎯 GERENCIADOR DO DASHBOARD MASTER - HEADER OVERLAY")
    print("=" * 60)
    
    manager = DashboardManagerOverlay()
    
    while True:
        print(f"\n📋 MENU:")
        print("1. 🎯 Adicionar análise header overlay")
        print("2. 📁 Criar grupo")
        print("3. 📋 Listar estrutura")
        print("4. 🗑️  Remover item")
        print("5. 🌐 Gerar Dashboard Master overlay")
        print("6. 📤 Exportar configuração")
        print("7. 📥 Importar configuração") 
        print("8. 🔍 Verificar status overlay")
        print("9. ❌ Sair")
        
        choice = input("\n👉 Escolha uma opção: ").strip()
        
        if choice == "1":
            print("\n🎯 ADICIONAR ANÁLISE HEADER OVERLAY")
            print("-" * 40)
            name = input("Nome da análise: ").strip()
            if not name:
                print("❌ Nome é obrigatório")
                continue
            
            filename = input("Nome do arquivo HTML (gerado com criar_dashboard_header_overlay.py): ").strip()
            if not filename:
                print("❌ Nome do arquivo é obrigatório")
                continue
            
            if not filename.endswith('.html'):
                filename += '.html'
            
            group = input("Grupo (deixe vazio para item individual): ").strip() or None
            icon = input("Ícone (emoji, deixe vazio para 🎯): ").strip() or "🎯"
            description = input("Descrição (opcional): ").strip()
            
            manager.add_overlay_analysis(name, filename, group, icon, description)
        
        elif choice == "2":
            print("\n📁 CRIAR GRUPO")
            print("-" * 20)
            name = input("Nome do grupo: ").strip()
            if not name:
                print("❌ Nome é obrigatório")
                continue
            
            icon = input("Ícone (emoji, deixe vazio para 📁): ").strip() or "📁"
            manager.create_group(name, icon)
        
        elif choice == "3":
            manager.list_items()
        
        elif choice == "4":
            print("\n🗑️  REMOVER ITEM")
            print("-" * 20)
            manager.list_items()
            item_id = input("\nID do item para remover: ").strip()
            if item_id:
                confirm = input(f"Confirma remoção de '{item_id}'? (s/N): ").strip().lower()
                if confirm == 's':
                    manager.remove_item(item_id)
                else:
                    print("Operação cancelada")
        
        elif choice == "5":
            print("\n🌐 GERAR DASHBOARD MASTER OVERLAY")
            print("-" * 40)
            output_name = input("Nome do arquivo (deixe vazio para 'dashboard_master_header_overlay_generated.html'): ").strip()
            if not output_name:
                output_name = "dashboard_master_header_overlay_generated.html"
            
            if not output_name.endswith('.html'):
                output_name += '.html'
                
            manager.generate_dashboard_overlay(output_name)
        
        elif choice == "6":
            print("\n📤 EXPORTAR CONFIGURAÇÃO")
            print("-" * 30)
            export_name = "dashboard_overlay_config_export.json"
            
            try:
                with open(export_name, 'w', encoding='utf-8') as f:
                    json.dump(manager.config, f, ensure_ascii=False, indent=2)
                print(f"✅ Configuração exportada para {export_name}")
            except Exception as e:
                print(f"❌ Erro na exportação: {e}")
        
        elif choice == "7":
            print("\n📥 IMPORTAR CONFIGURAÇÃO")
            print("-" * 30)
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
            print("\n🔍 STATUS DO SISTEMA OVERLAY")
            print("=" * 40)
            
            total_items = 0
            overlay_items = 0
            
            for item in manager.config["items"]:
                if item.get("type") == "file":
                    total_items += 1
                    if item.get("overlay"):
                        overlay_items += 1
                elif item.get("type") == "group":
                    for child in item.get("children", []):
                        total_items += 1
                        if child.get("overlay"):
                            overlay_items += 1
            
            print(f"📊 Total de análises: {total_items}")
            print(f"🎯 Análises com header overlay: {overlay_items}")
            print(f"📱 Taxa de overlay: {(overlay_items/total_items*100):.1f}%" if total_items > 0 else "0%")
            
            print(f"\n🏗️  Arquitetura: {manager.config.get('architecture', 'padrão')}")
            
            if overlay_items < total_items:
                print(f"\n💡 Para converter análises para header overlay:")
                print(f"   1. Regenere com criar_dashboard_header_overlay.py")
                print(f"   2. Substitua arquivos antigos") 
                print(f"   3. Atualize configuração do menu")
        
        elif choice == "9":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
