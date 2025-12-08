#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Manager - Versão 2.0
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
        self.emoji_options = self.get_emoji_options()
        self.templates = self.get_predefined_templates()
    
    def load_config(self) -> Dict[str, Any]:
        """Carrega configuração existente ou cria uma nova"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Erro ao carregar config: {e}")
        
        return {
            "title": "Dashboard Master - Versão 2.0",
            "created": datetime.now().isoformat(),
            "architecture": "v2_overlay",
            "description": "Sistema onde header SPSS sobrepõe interface com navegação lateral otimizada",
            "client_logo": "",  # URL da logomarca do cliente
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
    
    def get_emoji_options(self) -> Dict[str, List[str]]:
        """Retorna opções de emojis organizadas por categoria"""
        return {
            "analytics": ["📊", "📈", "📉", "💹", "🎯", "📋", "📌", "📍", "🔍", "🔎"],
            "business": ["💼", "🏢", "💰", "💳", "🏦", "📈", "📊", "🎯", "⚡", "🚀"],
            "communication": ["💬", "📱", "📧", "📞", "🌐", "📡", "📤", "📥", "📨", "📩"],
            "files": ["📁", "📂", "📄", "📋", "📊", "📈", "📉", "🗂️", "🗃️", "📚"],
            "tools": ["🔧", "🛠️", "⚙️", "🔩", "🔨", "⚡", "🔋", "💡", "🔌", "🖥️"],
            "medical": ["🏥", "⚕️", "💊", "🩺", "💉", "🧬", "🔬", "🧪", "📊", "📈"],
            "education": ["🎓", "📚", "📖", "✏️", "📝", "🔍", "💡", "🧠", "📊", "📈"],
            "social": ["👥", "👫", "👬", "👭", "🤝", "💬", "🗣️", "👤", "👥", "🌍"],
            "general": ["⭐", "✨", "🎉", "🎊", "🏆", "🥇", "🎖️", "🏅", "💎", "🔥"]
        }
    
    def get_predefined_templates(self) -> Dict[str, Dict]:
        """Retorna templates predefinidos para diferentes tipos de dashboard"""
        return {
            "analise_medica": {
                "title": "Dashboard Master - Análises Médicas",
                "description": "Template para análises médicas e hospitalares",
                "items": [
                    {"id": "home", "title": "Início", "icon": "🏠", "type": "action", "action": "showWelcome"},
                    {
                        "id": "pacientes", "title": "Pacientes", "icon": "🏥", "type": "group", "expanded": False,
                        "children": [
                            {"id": "demograficos", "title": "Dados Demográficos", "file": "pacientes_demograficos.html", "overlay": True},
                            {"id": "historico", "title": "Histórico Médico", "file": "pacientes_historico.html", "overlay": True}
                        ]
                    },
                    {
                        "id": "diagnosticos", "title": "Diagnósticos", "icon": "⚕️", "type": "group", "expanded": False,
                        "children": [
                            {"id": "freq_diagnosticos", "title": "Frequência de Diagnósticos", "file": "diagnosticos_freq.html", "overlay": True},
                            {"id": "comorbidades", "title": "Comorbidades", "file": "diagnosticos_comorbidades.html", "overlay": True}
                        ]
                    }
                ]
            },
            "pesquisa_academica": {
                "title": "Dashboard Master - Pesquisa Acadêmica",
                "description": "Template para análises de pesquisa científica",
                "items": [
                    {"id": "home", "title": "Início", "icon": "🏠", "type": "action", "action": "showWelcome"},
                    {
                        "id": "dados", "title": "Dados da Pesquisa", "icon": "📊", "type": "group", "expanded": False,
                        "children": [
                            {"id": "descritivos", "title": "Análise Descritiva", "file": "pesquisa_descritivos.html", "overlay": True},
                            {"id": "correlacoes", "title": "Correlações", "file": "pesquisa_correlacoes.html", "overlay": True}
                        ]
                    },
                    {
                        "id": "resultados", "title": "Resultados", "icon": "🎯", "type": "group", "expanded": False,
                        "children": [
                            {"id": "hipoteses", "title": "Teste de Hipóteses", "file": "resultados_hipoteses.html", "overlay": True},
                            {"id": "regressao", "title": "Análise de Regressão", "file": "resultados_regressao.html", "overlay": True}
                        ]
                    }
                ]
            },
            "marketing": {
                "title": "Dashboard Master - Análises de Marketing",
                "description": "Template para análises de marketing e vendas",
                "items": [
                    {"id": "home", "title": "Início", "icon": "🏠", "type": "action", "action": "showWelcome"},
                    {
                        "id": "clientes", "title": "Clientes", "icon": "👥", "type": "group", "expanded": False,
                        "children": [
                            {"id": "segmentacao", "title": "Segmentação", "file": "clientes_segmentacao.html", "overlay": True},
                            {"id": "satisfacao", "title": "Satisfação", "file": "clientes_satisfacao.html", "overlay": True}
                        ]
                    },
                    {
                        "id": "campanhas", "title": "Campanhas", "icon": "📈", "type": "group", "expanded": False,
                        "children": [
                            {"id": "performance", "title": "Performance", "file": "campanhas_performance.html", "overlay": True},
                            {"id": "roi", "title": "ROI", "file": "campanhas_roi.html", "overlay": True}
                        ]
                    }
                ]
            }
        }
    
    def save_config(self):
        """Salva configuração no arquivo"""
        self.config["updated"] = datetime.now().isoformat()
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"✅ Configuração v2.0 salva em {self.config_file}")
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
    
    def apply_template(self, template_name: str):
        """Aplica um template predefinido"""
        if template_name not in self.templates:
            print(f"❌ Template '{template_name}' não encontrado")
            return False
        
        template = self.templates[template_name]
        
        # Preserva configurações importantes
        old_created = self.config.get("created", datetime.now().isoformat())
        old_logo = self.config.get("client_logo", "")
        
        # Aplica o template
        self.config.update(template)
        self.config["created"] = old_created
        self.config["client_logo"] = old_logo
        self.config["template_applied"] = template_name
        self.config["template_applied_at"] = datetime.now().isoformat()
        
        self.save_config()
        print(f"✅ Template '{template_name}' aplicado com sucesso!")
        return True
    
    def update_client_logo(self, logo_url: str):
        """Atualiza a URL da logomarca do cliente"""
        self.config["client_logo"] = logo_url.strip()
        self.save_config()
        print(f"✅ Logomarca do cliente atualizada: {logo_url}")
    
    def show_emoji_options(self):
        """Exibe opções de emojis organizadas por categoria"""
        print("\n🎨 OPÇÕES DE EMOJIS POR CATEGORIA:")
        print("=" * 50)
        
        for category, emojis in self.emoji_options.items():
            category_names = {
                "analytics": "📊 Análise e Dados",
                "business": "💼 Negócios",
                "communication": "💬 Comunicação", 
                "files": "📁 Arquivos e Documentos",
                "tools": "🔧 Ferramentas",
                "medical": "🏥 Médico e Saúde",
                "education": "🎓 Educação e Pesquisa",
                "social": "👥 Social e Pessoas",
                "general": "⭐ Geral"
            }
            
            print(f"\n{category_names.get(category, category.title())}:")
            emoji_line = "  ".join(emojis)
            print(f"  {emoji_line}")
        
        print(f"\n💡 Dica: Copie e cole o emoji desejado ou digite manualmente")
    
    def show_templates(self):
        """Exibe templates predefinidos disponíveis"""
        print("\n📋 TEMPLATES PREDEFINIDOS DISPONÍVEIS:")
        print("=" * 50)
        
        for i, (template_key, template_data) in enumerate(self.templates.items(), 1):
            print(f"\n{i}. {template_data['title']}")
            print(f"   🏷️  ID: {template_key}")
            print(f"   📝 {template_data['description']}")
            
            # Conta itens do template
            total_groups = len([item for item in template_data['items'] if item.get('type') == 'group'])
            total_files = sum(len(item.get('children', [])) for item in template_data['items'] if item.get('type') == 'group')
            
            print(f"   📊 Contém: {total_groups} grupos, {total_files} análises")
    
    def edit_item_properties(self, item_id: str):
        """Edita propriedades de um item (nome, emoji, etc.)"""
        # Procura o item
        item_found = None
        parent_group = None
        
        # Busca em itens principais
        for item in self.config["items"]:
            if item["id"] == item_id:
                item_found = item
                break
        
        # Busca em subitens
        if not item_found:
            for group in self.config["items"]:
                if group.get("type") == "group" and "children" in group:
                    for child in group["children"]:
                        if child["id"] == item_id:
                            item_found = child
                            parent_group = group
                            break
                    if item_found:
                        break
        
        if not item_found:
            print(f"❌ Item '{item_id}' não encontrado")
            return False
        
        print(f"\n✏️ EDITANDO ITEM: {item_found['title']}")
        print("-" * 40)
        print(f"Atual: {item_found.get('icon', '📄')} {item_found['title']}")
        
        # Editar nome
        new_name = input(f"Novo nome (Enter para manter '{item_found['title']}'): ").strip()
        if new_name:
            item_found['title'] = new_name
            print(f"✅ Nome atualizado para: {new_name}")
        
        # Editar emoji
        print(f"\n💡 Dica: Use opção 9 do menu para ver emojis disponíveis")
        current_icon = item_found.get('icon', '📄')
        new_icon = input(f"Novo emoji (Enter para manter '{current_icon}'): ").strip()
        if new_icon:
            item_found['icon'] = new_icon
            print(f"✅ Emoji atualizado para: {new_icon}")
        
        # Editar descrição se existir
        if 'description' in item_found:
            current_desc = item_found.get('description', '')
            new_desc = input(f"Nova descrição (Enter para manter): ").strip()
            if new_desc:
                item_found['description'] = new_desc
                print(f"✅ Descrição atualizada")
        
        self.save_config()
        return True
    
    def reorder_items(self):
        """Permite reordenar itens do menu"""
        print(f"\n📋 REORDENAR ITENS DO MENU")
        print("=" * 30)
        
        # Lista itens atuais
        print("Ordem atual:")
        for i, item in enumerate(self.config["items"], 1):
            icon = item.get('icon', '📄')
            print(f"{i}. {icon} {item['title']} (ID: {item['id']})")
        
        print(f"\nDigite a nova ordem usando os números, separados por vírgula")
        print(f"Exemplo: 2,1,3,4 (move o item 2 para primeiro lugar)")
        
        try:
            order_input = input("Nova ordem: ").strip()
            if not order_input:
                print("Operação cancelada")
                return
            
            # Parse da nova ordem
            new_order = [int(x.strip()) - 1 for x in order_input.split(',')]
            
            if len(new_order) != len(self.config["items"]):
                print(f"❌ Erro: Digite {len(self.config['items'])} números")
                return
            
            if sorted(new_order) != list(range(len(self.config["items"]))):
                print(f"❌ Erro: Use todos os números de 1 a {len(self.config['items'])}")
                return
            
            # Reordena
            old_items = self.config["items"].copy()
            self.config["items"] = [old_items[i] for i in new_order]
            
            self.save_config()
            print(f"✅ Ordem atualizada com sucesso!")
            
            # Mostra nova ordem
            print(f"\nNova ordem:")
            for i, item in enumerate(self.config["items"], 1):
                icon = item.get('icon', '📄')
                print(f"{i}. {icon} {item['title']}")
                
        except ValueError:
            print(f"❌ Erro: Digite apenas números separados por vírgula")
    
    def move_item_to_group(self, item_id: str, target_group_id: str = None):
        """Move um item para outro grupo ou para o nível principal"""
        # Encontra o item
        item_found = None
        source_location = None
        source_index = None
        
        # Busca em itens principais
        for i, item in enumerate(self.config["items"]):
            if item["id"] == item_id:
                item_found = item
                source_location = "main"
                source_index = i
                break
        
        # Busca em subitens
        if not item_found:
            for group in self.config["items"]:
                if group.get("type") == "group" and "children" in group:
                    for i, child in enumerate(group["children"]):
                        if child["id"] == item_id:
                            item_found = child
                            source_location = group
                            source_index = i
                            break
                    if item_found:
                        break
        
        if not item_found:
            print(f"❌ Item '{item_id}' não encontrado")
            return False
        
        # Remove item da localização atual
        if source_location == "main":
            self.config["items"].pop(source_index)
        else:
            source_location["children"].pop(source_index)
        
        # Adiciona na nova localização
        if target_group_id:
            # Procura o grupo alvo
            target_group = None
            for group in self.config["items"]:
                if group.get("type") == "group" and group["id"] == target_group_id:
                    target_group = group
                    break
            
            if target_group:
                target_group["children"].append(item_found)
                print(f"✅ Item '{item_found['title']}' movido para grupo '{target_group['title']}'")
            else:
                # Grupo não encontrado, volta para posição original
                if source_location == "main":
                    self.config["items"].insert(source_index, item_found)
                else:
                    source_location["children"].insert(source_index, item_found)
                print(f"❌ Grupo '{target_group_id}' não encontrado")
                return False
        else:
            # Move para nível principal
            self.config["items"].append(item_found)
            print(f"✅ Item '{item_found['title']}' movido para nível principal")
        
        self.save_config()
        return True
    
    def menu_editor_interface(self):
        """Interface completa de edição do menu"""
        while True:
            print(f"\n✏️ EDITOR DE MENU")
            print("=" * 20)
            print("1. 📝 Editar nome/emoji de item")
            print("2. 📋 Reordenar itens")
            print("3. 🔄 Mover item entre grupos")
            print("4. 📋 Ver estrutura atual")
            print("5. ↩️ Voltar ao menu principal")
            
            choice = input("\n👉 Escolha uma opção: ").strip()
            
            if choice == "1":
                self.list_items()
                item_id = input("\nID do item para editar: ").strip()
                if item_id:
                    self.edit_item_properties(item_id)
            
            elif choice == "2":
                self.reorder_items()
            
            elif choice == "3":
                print(f"\n🔄 MOVER ITEM ENTRE GRUPOS")
                print("-" * 30)
                self.list_items()
                
                item_id = input("\nID do item para mover: ").strip()
                if not item_id:
                    continue
                
                print(f"\nGrupos disponíveis:")
                for item in self.config["items"]:
                    if item.get("type") == "group":
                        print(f"  • {item['id']} - {item['title']}")
                
                target = input("\nID do grupo destino (Enter = nível principal): ").strip()
                target = target if target else None
                
                self.move_item_to_group(item_id, target)
            
            elif choice == "4":
                self.list_items()
            
            elif choice == "5":
                break
            
            else:
                print("❌ Opção inválida")
    
    def add_overlay_analysis(self, name: str, filename: str, group: str = None, icon: str = "🎯", description: str = ""):
        """Adiciona nova análise v2.0 ao menu"""
        item_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c').replace('õ', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        
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
        group_id = name.lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c').replace('õ', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        
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
        print("\n📋 ESTRUTURA DO MENU v2.0:")
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
    
    def generate_dashboard_overlay(self, output_file="index.html"):
        """Gera o Dashboard Master versão 2.0"""
        
        # Template HTML otimizado para versão 2.0
        html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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
            padding: 20px 10px;
            border-bottom: 1px solid var(--border);
            background: #ffffff;
            color: var(--text);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100px;
        }}

        .sidebar.collapsed .sidebar-header {{
            padding: 10px 5px;
            min-height: 60px;
        }}

        .client-logo {{
            width: 160px;
            height: 100px;
            object-fit: contain;
            transition: all 0.3s ease;
            border-radius: 0;
            background: transparent;
            padding: 0;
            border: none;
        }}

        .sidebar.collapsed .client-logo {{
            width: 55px;
            height: 45px;
        }}

        .logo-placeholder {{
            width: 120px;
            height: 80px;
            background: transparent;
            border-radius: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
            font-size: 32px;
            transition: all 0.3s ease;
        }}

        .sidebar.collapsed .logo-placeholder {{
            width: 45px;
            height: 35px;
            font-size: 20px;
        }}

        .sidebar-toggle-container {{
            position: absolute;
            bottom: 12px;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: center;
        }}

        .sidebar-toggle-btn {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: transparent;
            color: var(--primary);
            border: 1px solid var(--primary);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 18px;
        }}

        .sidebar-toggle-btn:hover {{
            background: var(--primary);
            color: white;
        }}

        .sidebar.collapsed .sidebar-toggle-btn i {{
            transform: rotate(180deg);
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
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo-container">
                    {logo_html}
                </div>
            </div>

            <nav class="sidebar-menu" id="sidebarMenu">
                <!-- Menu será gerado dinamicamente -->
            </nav>

            <div class="sidebar-toggle-container">
                <button id="sidebarToggle" class="sidebar-toggle-btn" onclick="toggleSidebar()">
                    <i id="sidebarToggleIcon" class="fa fa-chevron-left"></i>
                </button>
            </div>
        </div>

        <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobileSidebar()"></div>

        <div class="main-content">
            <iframe class="content-frame" id="contentFrame" style="display: none;"></iframe>
            
            <div class="welcome" id="welcomeState" style="display: none;">
                <div class="welcome-icon">🎯</div>
                <h2>{title}</h2>
                <p>Sistema otimizado onde análises SPSS sobrepõem toda a interface com header próprio, mantendo apenas sidebar para navegação.</p>
                
                <div class="feature-highlight">
                    <h3>🚀 Arquitetura v2.0</h3>
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
                        <li>Gere análises com <code>criar_dashboard_v2.py</code></li>
                        <li>Adicione no menu usando este gerenciador</li>
                        <li>Navegue - cada análise ocupa toda a tela</li>
                        <li>Use sidebar para trocar entre análises</li>
                    </ol>
                </div>
            </div>

            <div class="loading" id="loadingState" style="display: none;">
                <div class="loading-spinner"></div>
                Carregando Dados...
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
            const icon = document.getElementById("sidebarToggleIcon");
            
            if (isMobile) {{
                sidebar.classList.toggle('mobile-open');
                document.getElementById('mobileOverlay').classList.toggle('active');
            }} else {{
                if (currentSidebarState === 'expanded') {{
                    sidebar.classList.add('collapsed');
                    icon.classList.remove('fa-chevron-left');
                    icon.classList.add('fa-chevron-right');
                    currentSidebarState = 'collapsed';
                }} else {{
                    sidebar.classList.remove('collapsed');
                    icon.classList.remove('fa-chevron-right');
                    icon.classList.add('fa-chevron-left');
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
                    console.log(`✅ ${{item.title}} carregado v2.0`);
                }};

                frame.onerror = () => {{
                    loading.style.display = 'none';
                    welcome.style.display = 'flex';
                    welcome.innerHTML = `
                        <div class="welcome-icon" style="color: #ef4444;">❌</div>
                        <h2 style="color: #ef4444;">Arquivo não encontrado</h2>
                        <p>O arquivo "${{item.file}}" não foi encontrado.</p>
                        <div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; color: #92400e;">
                            <strong>💡 Dica:</strong> Use o <code>criar_dashboard_v2.py</code> 
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
            loadFirstMenuItem();
            
            console.log('🎯 Dashboard Master v2.0 carregado!');
        }});

        function loadFirstMenuItem() {{
            // Procura o primeiro item que não é "home" (início)
            for (let item of menuConfig.items) {{
                if (item.type === 'file' && item.file) {{
                    // Carrega primeiro arquivo individual
                    loadContent(item);
                    document.querySelector(`[data-id="${{item.id}}"]`)?.classList.add('active');
                    return;
                }} else if (item.type === 'group' && item.children && item.children.length > 0) {{
                    // Carrega primeiro item do primeiro grupo
                    const firstChild = item.children.find(child => child.file);
                    if (firstChild) {{
                        loadContent(firstChild);
                        
                        // Expande o grupo e marca item ativo
                        const groupElement = document.querySelector(`[data-id="${{item.id}}"]`);
                        if (groupElement) {{
                            groupElement.classList.add('expanded');
                            const childElement = document.querySelector(`[data-id="${{firstChild.id}}"]`);
                            if (childElement) {{
                                childElement.classList.add('active');
                            }}
                        }}
                        return;
                    }}
                }}
            }}
            
            // Fallback: se não encontrar nenhum item, esconde welcome e mostra tela vazia
            const frame = document.getElementById('contentFrame');
            const welcome = document.getElementById('welcomeState');
            const loading = document.getElementById('loadingState');
            
            welcome.style.display = 'none';
            frame.style.display = 'none';
            loading.style.display = 'none';
        }}

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
        
        # Conta itens v2.0
        for item in self.config["items"]:
            if item.get("type") == "file" and item.get("overlay"):
                total_overlay += 1
            elif item.get("type") == "group":
                for child in item.get("children", []):
                    if child.get("overlay"):
                        total_overlay += 1
        
        stats_text = f"{total_groups} grupos • {total_files} individuais • {total_subitems} subitens • {total_overlay} overlay"
        
        # Gera HTML do logo do cliente
        client_logo = self.config.get("client_logo", "").strip()
        if client_logo:
            logo_html = f'<img src="{client_logo}" alt="Logo do Cliente" class="client-logo" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';" /><div class="logo-placeholder" style="display:none;">🏢</div>'
        else:
            logo_html = '<div class="logo-placeholder">🏢</div>'
        
        # Gera HTML
        html_content = html_template.format(
            title=self.config["title"],
            logo_html=logo_html,
            menu_config_json=json.dumps(self.config, ensure_ascii=False)
        )
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ Dashboard Master v2.0 gerado: {output_file}")
            print(f"🎯 Funcionalidades:")
            print(f"   • Header SPSS sobrepõe toda a interface")
            print(f"   • Sidebar mínima para navegação")
            print(f"   • Máximo aproveitamento de espaço")
            print(f"   • {total_overlay} análises com overlay configuradas")
        except Exception as e:
            print(f"❌ Erro ao gerar HTML: {e}")

def main():
    print("🎯 GERENCIADOR DO DASHBOARD MASTER v2.0")
    print("=" * 60)
    
    manager = DashboardManagerOverlay()
    
    while True:
        print(f"\n📋 MENU:")
        print("1. 🎯 Adicionar análise v2.0")
        print("2. 📁 Criar grupo")
        print("3. 📋 Listar estrutura")
        print("4. 🗑️  Remover item")
        print("5. 🌐 Gerar Dashboard Master overlay")
        print("6. 📤 Exportar configuração")
        print("7. 📥 Importar configuração") 
        print("8. 🔍 Verificar status overlay")
        print("9. 🎨 Ver opções de emojis")
        print("10. 📋 Ver templates predefinidos")
        print("11. 🎯 Aplicar template predefinido")
        print("12. 🏢 Atualizar logo do cliente")
        print("13. ✏️ Editor de menu (reordenar, editar)")
        print("14. ❌ Sair")
        
        choice = input("\n👉 Escolha uma opção: ").strip()
        
        if choice == "1":
            print("\n🎯 ADICIONAR ANÁLISE v2.0")
            print("-" * 40)
            name = input("Nome da análise: ").strip()
            if not name:
                print("❌ Nome é obrigatório")
                continue
            
            filename = input("Nome do arquivo HTML (gerado com criar_dashboard_v2.py): ").strip()
            if not filename:
                print("❌ Nome do arquivo é obrigatório")
                continue
            
            if not filename.endswith('.html'):
                filename += '.html'
            
            group = input("Grupo (deixe vazio para item individual): ").strip() or None
            
            print("\n💡 Dica: Use a opção 9 do menu para ver categorias de emojis disponíveis")
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
            
            print("\n💡 Dica: Use a opção 9 do menu para ver categorias de emojis disponíveis")
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
            output_name = input("Nome do arquivo (deixe vazio para 'index.html'): ").strip()
            if not output_name:
                output_name = "index.html"
            
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
            print(f"🎯 Análises v2.0: {overlay_items}")
            print(f"📱 Taxa de overlay: {(overlay_items/total_items*100):.1f}%" if total_items > 0 else "0%")
            
            print(f"\n🏗️  Arquitetura: {manager.config.get('architecture', 'padrão')}")
            
            if overlay_items < total_items:
                print(f"\n💡 Para converter análises para v2.0:")
                print(f"   1. Regenere com criar_dashboard_v2.py")
                print(f"   2. Substitua arquivos antigos") 
                print(f"   3. Atualize configuração do menu")
        
        elif choice == "9":
            manager.show_emoji_options()
        
        elif choice == "10":
            manager.show_templates()
        
        elif choice == "11":
            print("\n🎯 APLICAR TEMPLATE PREDEFINIDO")
            print("-" * 40)
            manager.show_templates()
            
            template_id = input("\nDigite o ID do template para aplicar: ").strip()
            if template_id:
                confirm = input(f"⚠️  Isso substituirá a configuração atual. Confirma? (s/N): ").strip().lower()
                if confirm == 's':
                    if manager.apply_template(template_id):
                        print("✅ Template aplicado! Você pode agora personalizar as análises.")
                    else:
                        print("❌ Template não encontrado")
                else:
                    print("Operação cancelada")
        
        elif choice == "12":
            print("\n🏢 ATUALIZAR LOGO DO CLIENTE")
            print("-" * 40)
            current_logo = manager.config.get("client_logo", "")
            if current_logo:
                print(f"Logo atual: {current_logo}")
            else:
                print("Nenhum logo configurado")
            
            print("\n💡 Dicas:")
            print("• Use URLs diretas para imagens (PNG, JPG, SVG)")
            print("• Tamanho recomendado: 200x150px ou menor")
            print("• Deixe vazio para remover o logo atual")
            
            new_logo = input("\nURL do novo logo (ou Enter para remover): ").strip()
            manager.update_client_logo(new_logo)
        
        elif choice == "13":
            manager.menu_editor_interface()
        
        elif choice == "14":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
