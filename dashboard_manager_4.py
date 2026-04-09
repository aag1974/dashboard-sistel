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
            "password": "",  # Senha de acesso (vazio = sem senha)
            "welcome_title": "",  # Título na tela de boas-vindas (vazio = usa title)
            "welcome_message": "Selecione uma análise no menu lateral para começar.",  # Mensagem de boas-vindas
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
    
    def reorder_submenu(self, group_id: str = None):
        """Reordena subitens de um grupo. Se group_id não informado, pergunta."""
        
        # Listar grupos disponíveis
        groups = [item for item in self.config["items"] if item.get("type") == "group"]
        if not groups:
            print("❌ Nenhum grupo encontrado.")
            return
        
        # Selecionar grupo
        if not group_id:
            print(f"\n📁 GRUPOS DISPONÍVEIS:")
            for i, g in enumerate(groups, 1):
                n = len(g.get("children", []))
                print(f"  {i}. {g.get('icon','📁')} {g['title']} ({n} item{'ns' if n!=1 else ''})")
            
            try:
                choice = input("\nNúmero do grupo: ").strip()
                if not choice:
                    print("Operação cancelada.")
                    return
                idx = int(choice) - 1
                if idx < 0 or idx >= len(groups):
                    print("❌ Número inválido.")
                    return
                group = groups[idx]
            except ValueError:
                print("❌ Digite um número.")
                return
        else:
            group = next((g for g in groups if g["id"] == group_id), None)
            if not group:
                print(f"❌ Grupo '{group_id}' não encontrado.")
                return
        
        children = group.get("children", [])
        if not children:
            print(f"❌ O grupo '{group['title']}' não tem subitens.")
            return
        
        print(f"\n📋 REORDENAR SUBITENS DE: {group.get('icon','📁')} {group['title']}")
        print("=" * 40)
        print("Ordem atual:")
        for i, child in enumerate(children, 1):
            print(f"  {i}. {child['title']}")
        
        print(f"\nDigite a nova ordem com os números separados por vírgula.")
        print(f"Exemplo: 3,1,2  (move o 3º para primeiro)")
        
        try:
            order_input = input("Nova ordem: ").strip()
            if not order_input:
                print("Operação cancelada.")
                return
            
            new_order = [int(x.strip()) - 1 for x in order_input.split(',')]
            
            if len(new_order) != len(children):
                print(f"❌ Erro: Digite exatamente {len(children)} números.")
                return
            
            if sorted(new_order) != list(range(len(children))):
                print(f"❌ Erro: Use todos os números de 1 a {len(children)} sem repetição.")
                return
            
            old = children.copy()
            group["children"] = [old[i] for i in new_order]
            
            self.save_config()
            print(f"\n✅ Subitens de '{group['title']}' reordenados!")
            print("Nova ordem:")
            for i, child in enumerate(group["children"], 1):
                print(f"  {i}. {child['title']}")
        
        except ValueError:
            print("❌ Erro: Digite apenas números separados por vírgula.")

    def menu_editor_interface(self):
        """Interface completa de edição do menu"""
        while True:
            print(f"\n✏️ EDITOR DE MENU")
            print("=" * 20)
            print("1. 📝 Editar nome/emoji de item")
            print("2. 📋 Reordenar grupos do menu principal")
            print("3. 📋 Reordenar subitens de um grupo")
            print("4. 🔄 Mover item entre grupos")
            print("5. 📋 Ver estrutura atual")
            print("6. ↩️ Voltar ao menu principal")
            
            choice = input("\n👉 Escolha uma opção: ").strip()
            
            if choice == "1":
                self.list_items()
                item_id = input("\nID do item para editar: ").strip()
                if item_id:
                    self.edit_item_properties(item_id)
            
            elif choice == "2":
                self.reorder_items()
            
            elif choice == "3":
                self.reorder_submenu()
            
            elif choice == "4":
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
            
            elif choice == "5":
                self.list_items()
            
            elif choice == "6":
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
        """Gera o Dashboard Master versão 3.1 — identidade visual Opinião"""
        
        html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --teal: #7BAFC0;
            --teal-dark: #4d8a9e;
            --teal-light: #EDF5F7;
            --green: #6FAB8A;
            --green-dark: #3d8a62;
            --red: #B83B5C;
            --bg: #f8f9fa;
            --text: #333;
            --text-light: #6c757d;
            --border: #e5e5e5;
            --hover: #f4f8f9;
            --active-bg: #EDF5F7;
            --active-border: #7BAFC0;
            --active-text: #4d8a9e;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); color: var(--text);
            overflow: hidden; height: 100vh;
        }}
        .dashboard-container {{ display: flex; height: 100vh; }}

        /* ── SIDEBAR ── */
        .sidebar {{
            width: 220px; background: white;
            box-shadow: 4px 0 16px rgba(0,0,0,0.08);
            display: flex; flex-direction: column;
            flex-shrink: 0; transition: width 0.25s ease; z-index: 1000;
        }}
        .sidebar.collapsed {{ width: 52px; }}

        .sidebar-logo {{
            padding: 12px 14px;
            border-bottom: 0.5px solid var(--border);
            display: flex; align-items: center; justify-content: center;
            min-height: 70px; overflow: hidden;
        }}
        .client-logo {{
            max-width: 148px; max-height: 52px;
            object-fit: contain; transition: all 0.25s;
        }}
        .sidebar.collapsed .client-logo {{ max-width: 30px; max-height: 30px; }}
        .logo-placeholder {{ font-size: 24px; color: var(--teal); }}

        .sidebar-menu {{
            flex: 1; overflow-y: auto; overflow-x: hidden; padding: 5px 0;
        }}
        .sidebar-menu::-webkit-scrollbar {{ width: 3px; }}
        .sidebar-menu::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

        .menu-item {{
            display: flex; align-items: center; gap: 10px;
            padding: 10px 16px 10px 18px; cursor: pointer;
            border-left: 2px solid transparent;
            font-size: 13px; color: var(--text);
            transition: background 0.15s, border-color 0.15s;
            position: relative; user-select: none;
        }}
        .menu-item:hover {{ background: var(--hover); border-left-color: var(--teal); }}
        .menu-item.active {{ background: var(--active-bg); border-left-color: var(--active-border); color: var(--active-text); font-weight: 500; }}
        .menu-item.group-open {{ color: var(--active-text); font-weight: 500; }}

        .menu-icon {{ font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }}
        .menu-text {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: opacity 0.2s; }}
        .sidebar.collapsed .menu-text {{ opacity: 0; pointer-events: none; }}

        .expand-icon {{
            font-size: 8px; color: #bbb;
            transition: transform 0.2s; flex-shrink: 0;
            order: -1;  /* move para antes do texto */
            width: 12px; text-align: center;
        }}
        .menu-item.group-open .expand-icon {{ transform: rotate(90deg); color: var(--teal); }}
        .sidebar.collapsed .expand-icon {{ display: none; }}

        .menu-tooltip {{
            display: none; position: absolute; left: 58px; top: 50%;
            transform: translateY(-50%); background: #222; color: #fff;
            padding: 4px 10px; border-radius: 5px; font-size: 12px;
            white-space: nowrap; pointer-events: none; z-index: 9999;
        }}
        .sidebar.collapsed .menu-item:hover .menu-tooltip {{ display: block; }}

        .submenu {{
            max-height: 0; overflow: hidden;
            transition: max-height 0.25s ease;
            background: rgba(123,175,192,0.03);
            border-left: 2px solid var(--border);
            margin-left: 30px;
        }}
        .submenu.open {{ max-height: 600px; }}
        .sidebar.collapsed .submenu {{ display: none; }}

        .submenu-item {{
            padding: 8px 16px 8px 14px;
            font-size: 13px; color: var(--text-light);
            cursor: pointer; border-left: 2px solid transparent;
            transition: background 0.15s, color 0.15s, border-color 0.15s;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .submenu-item:hover {{ background: var(--hover); border-left-color: var(--teal); color: var(--text); }}
        .submenu-item.active {{ background: var(--active-bg); border-left-color: var(--active-border); color: var(--active-text); font-weight: 500; }}

        /* ── RODAPÉ SIDEBAR ── */
        .sidebar-footer {{
            border-top: 0.5px solid var(--border);
            padding: 9px 11px;
            display: flex; align-items: center; gap: 8px; overflow: hidden;
        }}

        .opiniao-brand {{
            display: flex; align-items: center; gap: 7px;
            flex: 1; overflow: hidden; transition: opacity 0.2s;
        }}
        .sidebar.collapsed .opiniao-brand {{ opacity: 0; width: 0; pointer-events: none; }}

        .opiniao-logo-img {{
            height: 28px; width: auto; object-fit: contain; flex-shrink: 0;
        }}
        .opiniao-name {{
            font-size: 11px; font-weight: 600; color: #c0c0c0;
            white-space: nowrap;
        }}

        .toggle-btn {{
            width: 28px; height: 28px;
            border: 0.5px solid var(--border); border-radius: 6px;
            background: var(--bg); color: #aaa;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; font-size: 13px; flex-shrink: 0;
            transition: background 0.15s, color 0.15s;
            user-select: none;
        }}
        .toggle-btn:hover {{ background: #e9ecef; color: #555; }}

        /* ── MAIN CONTENT ── */
        .main-content {{ flex: 1; background: var(--bg); position: relative; overflow: hidden; }}
        .content-frame {{ width: 100%; height: 100vh; border: none; background: white; }}

        .loading {{
            display: flex; align-items: center; justify-content: center;
            height: 100vh; font-size: 15px; color: var(--text-light); background: white; gap: 12px;
        }}
        .loading-dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--teal); opacity: 0.3;
            animation: pulse 1.2s ease-in-out infinite;
        }}
        .loading-dot:nth-child(2) {{ animation-delay: 0.2s; }}
        .loading-dot:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes pulse {{ 0%,100%{{opacity:0.3;transform:scale(1)}} 50%{{opacity:1;transform:scale(1.3)}} }}

        .welcome {{
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            height: 100vh; text-align: center; padding: 60px 40px; background: white;
        }}
        .welcome-inner {{
            display: flex; align-items: center; gap: 64px;
            width: 100%; max-width: 860px;
        }}
        .welcome-stat-n {{ font-size: 40px; font-weight: 500; color: var(--teal-dark); }}
        .welcome-stat-lbl {{ font-size: 11px; color: #aaa; margin-top: 6px; text-transform: uppercase; letter-spacing: .05em; }}

        .error-state {{
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            height: 100vh; text-align: center; padding: 40px; background: white;
        }}
        .error-state h2 {{ color: var(--red); font-size: 16px; margin: 12px 0 8px; font-weight: 500; }}
        .error-state p {{ color: var(--text-light); font-size: 13px; }}

        @media (max-width: 768px) {{
            .sidebar {{ position: absolute; left: -220px; z-index: 2000; transition: left 0.25s; }}
            .sidebar.mobile-open {{ left: 0; }}
            .mobile-overlay {{ position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1500;display:none; }}
            .mobile-overlay.active {{ display: block; }}
        }}
    </style>
</head>
<body>
<div class="dashboard-container">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-logo">
            {logo_html}
        </div>
        <nav class="sidebar-menu" id="sidebarMenu"></nav>
        <div class="sidebar-footer">
            <div class="opiniao-brand">
                <img class="opiniao-logo-img" src="Logo_Opiniao.png"
                     onerror="this.style.display='none'"
                     alt="Opinião">
                <span class="opiniao-name"></span>
            </div>
            <div class="toggle-btn" id="toggleBtn" onclick="toggleSidebar()">‹</div>
        </div>
    </div>

    <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobile()"></div>

    <!-- TELA DE SENHA -->
    <div id="passwordScreen" style="
        position:fixed;top:0;left:0;right:0;bottom:0;
        background:#f4f7f9;display:flex;align-items:center;justify-content:center;
        z-index:9999;flex-direction:column;">
        <div style="background:white;border:0.5px solid #e5e5e5;border-radius:16px;
            padding:48px 56px;text-align:center;max-width:420px;width:90%;
            box-shadow:0 4px 32px rgba(0,0,0,0.08);">

            <!-- Logo do cliente -->
            <div id="pwLogoArea" style="margin-bottom:36px;min-height:20px;"></div>

            <!-- Aviso de conteúdo restrito em destaque -->
            <div style="background:#EDF5F7;border:0.5px solid rgba(123,175,192,0.35);
                border-radius:8px;padding:12px 16px;margin-bottom:28px;">
                <p style="font-size:13px;font-weight:600;color:#4d8a9e;margin:0;">
                    🔒 Conteúdo restrito
                </p>
                <p style="font-size:12px;color:#6c757d;margin:6px 0 0;line-height:1.5;">
                    Digite a senha fornecida para acessar este painel.
                </p>
            </div>

            <!-- Campo de senha -->
            <div style="position:relative;margin-bottom:12px;">
                <input type="password" id="pwInput" placeholder="Senha de acesso"
                    style="width:100%;padding:12px 44px 12px 14px;border:0.5px solid #ddd;border-radius:8px;
                        font-size:14px;outline:none;transition:border-color .15s;box-sizing:border-box;color:#333;"
                    onkeydown="if(event.key==='Enter')checkPassword()"
                    onfocus="this.style.borderColor='#7BAFC0'" onblur="this.style.borderColor='#ddd'">
                <span onclick="togglePwVis()" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);
                    cursor:pointer;font-size:15px;color:#bbb;user-select:none;" id="pwEye">👁</span>
            </div>
            <p id="pwError" style="color:#B83B5C;font-size:12px;margin-bottom:10px;min-height:18px;"></p>

            <!-- Botão entrar -->
            <button onclick="checkPassword()" style="width:100%;padding:12px;background:#7BAFC0;color:white;
                border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;letter-spacing:.02em;
                transition:background .15s;" onmouseover="this.style.background='#4d8a9e'"
                onmouseout="this.style.background='#7BAFC0'">Entrar</button>

            <!-- Rodapé Opinião -->
            <div style="margin-top:32px;padding-top:24px;border-top:0.5px solid #f0f0f0;">
                <p style="font-size:11px;color:#bbb;margin-bottom:8px;letter-spacing:.02em;">
                    Dashboard desenvolvido por
                </p>
                <img src="Logo_Opiniao.png" style="height:26px;opacity:.7;"
                    onerror="this.style.display='none'">
            </div>
        </div>
    </div>

    <div class="main-content">
        <iframe class="content-frame" id="contentFrame" style="display:none;"></iframe>
        <div class="welcome" id="welcomeState" style="display:none;flex-direction:row;align-items:stretch;padding:0;text-align:left;height:100vh;">
            <div style="width:280px;background:var(--teal-light);display:flex;flex-direction:column;justify-content:space-between;padding:40px 30px;flex-shrink:0;border-right:0.5px solid rgba(123,175,192,0.2);">
                <div>
                    <div style="font-size:11px;font-weight:600;color:var(--teal);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px;">Painel de Resultados</div>
                    <div style="font-size:18px;font-weight:500;color:#333;line-height:1.4;margin-bottom:20px;" id="welcomeTitle">Explore os resultados das pesquisas por tema</div>
                    <div style="height:0.5px;background:rgba(123,175,192,0.25);margin-bottom:20px;"></div>
                    <div style="font-size:13px;color:#6c757d;line-height:1.75;" id="welcomeMsg">Use o menu lateral para navegar entre os módulos. Cada tema apresenta análises detalhadas com gráficos interativos e filtros.</div>
                    <div style="display:flex;gap:10px;margin-top:24px;">
                        <div style="flex:1;text-align:center;background:white;border-radius:8px;padding:14px 8px;border:0.5px solid rgba(123,175,192,0.2);">
                            <div style="font-size:24px;font-weight:500;color:var(--teal-dark);" id="statTemas">—</div>
                            <div style="font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.05em;margin-top:4px;">Temas</div>
                        </div>
                        <div style="flex:1;text-align:center;background:white;border-radius:8px;padding:14px 8px;border:0.5px solid rgba(123,175,192,0.2);">
                            <div style="font-size:24px;font-weight:500;color:var(--teal-dark);" id="statPesquisas">—</div>
                            <div style="font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.05em;margin-top:4px;">Pesquisas</div>
                        </div>
                    </div>
                </div>
            </div>
            <div style="flex:1;display:flex;flex-direction:column;">
                <div style="flex:1;padding:36px 44px;overflow-y:auto;">
                    <div style="font-size:11px;font-weight:600;color:var(--teal);letter-spacing:.06em;text-transform:uppercase;margin-bottom:18px;">Temas disponíveis</div>
                    <div id="welcomeThemes" style="display:flex;flex-direction:column;gap:10px;"></div>
                </div>
                <div style="padding:16px 44px;border-top:0.5px solid #f0f0f0;">
                    <span style="font-size:12px;color:#bbb;">Dados que orientam decisões</span>
                </div>
            </div>
        </div>
                <div class="loading" id="loadingState" style="display:none;">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <span style="margin-left:8px;color:#aaa;font-size:13px">Carregando...</span>
        </div>
    </div>
</div>

<script>
    const menuConfig = {menu_config_json};
    const DASH_PASSWORD = menuConfig.password || '';
    const WELCOME_TITLE = menuConfig.welcome_title || menuConfig.title || '';
    const WELCOME_MSG   = menuConfig.welcome_message || 'Selecione uma análise no menu lateral para começar.';
    const CLIENT_LOGO   = menuConfig.client_logo || '';

    // Tela de senha
    function initPasswordScreen() {{
        if (!DASH_PASSWORD) {{
            document.getElementById('passwordScreen').style.display = 'none';
            initWelcome();
            return;
        }}
        // Verificar se já passou pela senha nesta sessão
        if (sessionStorage.getItem('dash_auth') === DASH_PASSWORD) {{
            document.getElementById('passwordScreen').style.display = 'none';
            initWelcome();
            return;
        }}
        // Mostrar logo na tela de senha
        if (CLIENT_LOGO) {{
            const pwImg = document.createElement('img');
            pwImg.src = CLIENT_LOGO;
            pwImg.style.cssText = 'max-height:64px;max-width:200px;object-fit:contain;';
            pwImg.onerror = function() {{ this.style.display='none'; }};
            document.getElementById('pwLogoArea').appendChild(pwImg);
        }}
    }}

    function checkPassword() {{
        const input = document.getElementById('pwInput').value;
        if (input === DASH_PASSWORD) {{
            sessionStorage.setItem('dash_auth', DASH_PASSWORD);
            document.getElementById('passwordScreen').style.display = 'none';
            initWelcome();
        }} else {{
            const err = document.getElementById('pwError');
            err.textContent = 'Senha incorreta. Tente novamente.';
            document.getElementById('pwInput').value = '';
            document.getElementById('pwInput').focus();
            setTimeout(() => {{ err.textContent = ''; }}, 3000);
        }}
    }}

    function togglePwVis() {{
        const inp = document.getElementById('pwInput');
        inp.type = inp.type === 'password' ? 'text' : 'password';
    }}

    function initWelcome() {{
        let nTemas = 0, nPesquisas = 0;
        const themesEl = document.getElementById('welcomeThemes');

        (menuConfig.items || []).forEach(item => {{
            if (item.type === 'group') {{
                nTemas++;
                if (themesEl) {{
                    const card = document.createElement('div');
                    card.style.cssText = 'display:flex;align-items:center;gap:14px;padding:14px 18px;border:0.5px solid #e5e5e5;border-radius:8px;cursor:pointer;transition:border-color .15s,background .15s;';
                    card.onmouseenter = function() {{ this.style.borderColor='#7BAFC0'; this.style.background='#f9fdfe'; }};
                    card.onmouseleave = function() {{ this.style.borderColor='#e5e5e5'; this.style.background='white'; }};
                    card.onclick = function() {{ renderMenu(); }};
                    const dot = document.createElement('div');
                    dot.style.cssText = 'width:8px;height:8px;border-radius:50%;background:#7BAFC0;flex-shrink:0;';
                    const name = document.createElement('span');
                    name.style.cssText = 'font-size:14px;color:#333;';
                    name.textContent = item.title;
                    card.appendChild(dot);
                    card.appendChild(name);
                    themesEl.appendChild(card);
                }}
                (item.children || []).forEach(child => {{ if (child.file) nPesquisas++; }});
            }} else if (item.file) {{
                nPesquisas++;
            }}
        }});

        const el = (id) => document.getElementById(id);
        if (el('statTemas'))     el('statTemas').textContent     = nTemas     || '—';
        if (el('statPesquisas')) el('statPesquisas').textContent = nPesquisas || '—';

        showWelcome();
    }}

    // Inicializar ao carregar
    window.addEventListener('DOMContentLoaded', initPasswordScreen);
    let collapsed = false;
    let isMobile = window.innerWidth <= 768;
    let currentAnalysisFrame = null;
    let analysisStats = {{ loaded:0, variables:0, filters:0, records:0 }};

    window.addEventListener('message', e => {{
        if (e.data && e.data.source === 'spss-analysis-overlay') {{
            const {{ type, data }} = e.data;
            if (type === 'analysis-loaded') {{
                analysisStats = {{ loaded:1, variables:data.variables, filters:data.filters, records:data.records }};
            }}
        }}
    }});

    function toggleSidebar() {{
        const sb = document.getElementById('sidebar');
        const btn = document.getElementById('toggleBtn');
        if (isMobile) {{
            sb.classList.toggle('mobile-open');
            document.getElementById('mobileOverlay').classList.toggle('active');
        }} else {{
            collapsed = !collapsed;
            sb.classList.toggle('collapsed', collapsed);
            btn.textContent = collapsed ? '›' : '‹';
        }}
    }}

    function closeMobile() {{
        document.getElementById('sidebar').classList.remove('mobile-open');
        document.getElementById('mobileOverlay').classList.remove('active');
    }}

    function renderMenu() {{
        const nav = document.getElementById('sidebarMenu');
        nav.innerHTML = '';
        menuConfig.items.forEach(item => {{
            if (item.type === 'group') renderGroup(nav, item);
            else renderItem(nav, item);
        }});
    }}

    function renderGroup(container, group) {{
        const el = document.createElement('div');
        el.className = 'menu-item' + (group.expanded ? ' group-open' : '');
        el.innerHTML = `
            <span class="menu-text">${{group.title}}</span>
            <span class="expand-icon">▶</span>
            <span class="menu-tooltip">${{group.title}}</span>`;
        container.appendChild(el);

        const sub = document.createElement('div');
        sub.className = 'submenu' + (group.expanded ? ' open' : '');
        container.appendChild(sub);

        el.addEventListener('click', () => {{
            group.expanded = !group.expanded;
            el.classList.toggle('group-open', group.expanded);
            sub.classList.toggle('open', group.expanded);
        }});

        (group.children || []).forEach(child => {{
            const si = document.createElement('div');
            si.className = 'submenu-item';
            si.textContent = child.title;
            si.addEventListener('click', e => {{
                e.stopPropagation();
                loadContent(child);
                setActive(si);
                if (isMobile) closeMobile();
            }});
            sub.appendChild(si);
        }});
    }}

    function renderItem(container, item) {{
        const el = document.createElement('div');
        el.className = 'menu-item';
        el.innerHTML = `
            <span class="menu-text">${{item.title}}</span>
            <span class="menu-tooltip">${{item.title}}</span>`;
        el.addEventListener('click', () => {{
            if (item.type === 'action' && item.action === 'showWelcome') showWelcome();
            else if (item.file) loadContent(item);
            setActive(el);
            if (isMobile) closeMobile();
        }});
        container.appendChild(el);
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
            frame.onload = () => {{ loading.style.display='none'; frame.style.display='block'; }};
            frame.onerror = () => {{
                loading.style.display = 'none';
                welcome.innerHTML = `<div class="error-state">
                    <div style="font-size:36px">⚠️</div>
                    <h2>Arquivo não encontrado</h2>
                    <p>${{item.file}}</p></div>`;
                welcome.style.display = 'flex';
            }};
        }}, 200);
    }}

    function showWelcome() {{
        document.getElementById('contentFrame').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('welcomeState').style.display = 'flex';
        currentAnalysisFrame = null;
    }}

    function setActive(el) {{
        document.querySelectorAll('.menu-item.active,.submenu-item.active').forEach(e => e.classList.remove('active'));
        el.classList.add('active');
    }}

    function sendCommand(cmd, data={{}}) {{
        if (currentAnalysisFrame) currentAnalysisFrame.postMessage({{ source:'dashboard-master', type:cmd, data }}, '*');
    }}

    window.addEventListener('resize', () => {{ isMobile = window.innerWidth <= 768; }});

    document.addEventListener('DOMContentLoaded', () => {{
        renderMenu();
        // Auto-carregar primeiro item com arquivo
        for (const item of menuConfig.items) {{
            if (item.file) {{ loadContent(item); return; }}
            if (item.type === 'group') {{
                const first = (item.children||[]).find(c => c.file);
                if (first) {{ loadContent(first); return; }}
            }}
        }}
        showWelcome();
    }});

    window.dashboardDebug = {{ stats: () => analysisStats, sendCommand }};
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
        print("1.  🎯 Adicionar análise")
        print("2.  📁 Criar grupo")
        print("3.  📋 Listar estrutura")
        print("4.  🗑️  Remover item")
        print("5.  🌐 Gerar Dashboard Master")
        print("6.  📤 Exportar configuração")
        print("7.  📥 Importar configuração")
        print("8.  🔍 Verificar status")
        print("9.  🎨 Ver opções de emojis")
        print("10. 📋 Ver templates predefinidos")
        print("11. 🎯 Aplicar template predefinido")
        print("12. 🏢 Atualizar logo do cliente")
        print("13. ✏️  Editor de menu (reordenar, editar)")
        print("14. 🔒 Configurar senha e boas-vindas")
        print("0.  ❌ Sair")
        
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
            print("\n🔒 CONFIGURAR SENHA E BOAS-VINDAS")
            print("-" * 40)

            # Senha
            current_pw = manager.config.get("password", "")
            if current_pw:
                print(f"Senha atual: {'*' * len(current_pw)} ({len(current_pw)} caracteres)")
            else:
                print("Senha atual: nenhuma (dashboard aberto)")

            new_pw = input("\nNova senha (Enter para manter, 'remover' para apagar): ").strip()
            if new_pw.lower() == 'remover':
                manager.config["password"] = ""
                print("✅ Senha removida — dashboard ficará sem proteção")
            elif new_pw:
                manager.config["password"] = new_pw
                print(f"✅ Senha definida: {new_pw}")
            else:
                print("Senha mantida sem alteração")

            # Título de boas-vindas
            current_wt = manager.config.get("welcome_title", "")
            print(f"\nTítulo de boas-vindas atual: '{current_wt or '(usa título geral)'}'")
            new_wt = input("Novo título (Enter para manter): ").strip()
            if new_wt:
                manager.config["welcome_title"] = new_wt
                print(f"✅ Título definido: {new_wt}")

            # Mensagem de boas-vindas
            current_wm = manager.config.get("welcome_message", "")
            print(f"\nMensagem atual: '{current_wm}'")
            new_wm = input("Nova mensagem (Enter para manter): ").strip()
            if new_wm:
                manager.config["welcome_message"] = new_wm
                print(f"✅ Mensagem definida")

            manager.save_config()
            print("\n💡 Regenere o dashboard (opção 5) para aplicar as alterações.")

        elif choice == "0":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
