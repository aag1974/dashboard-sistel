#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Rápido do Dashboard Master
Configuração automatizada com exemplos prontos
"""

import os
import json
from datetime import datetime

def create_sample_config():
    """Cria configuração de exemplo completa"""
    return {
        "title": "Dashboard Master - Opinião Informação Estratégica",
        "created": datetime.now().isoformat(),
        "items": [
            {
                "id": "home",
                "title": "Início",
                "icon": "🏠",
                "type": "action",
                "action": "showWelcome"
            },
            {
                "id": "pesquisas-mercado",
                "title": "Pesquisas de Mercado",
                "icon": "📈",
                "type": "group",
                "expanded": True,
                "children": [
                    {
                        "id": "perfil-consumidor",
                        "title": "Perfil do Consumidor",
                        "file": "perfil_consumidor_dashboard.html",
                        "description": "Análise demográfica e comportamental"
                    },
                    {
                        "id": "tendencias-mercado",
                        "title": "Tendências de Mercado",
                        "file": "tendencias_mercado_dashboard.html", 
                        "description": "Evolução do mercado e projeções"
                    },
                    {
                        "id": "concorrencia",
                        "title": "Análise da Concorrência",
                        "file": "analise_concorrencia_dashboard.html",
                        "description": "Posicionamento competitivo"
                    }
                ]
            },
            {
                "id": "satisfacao-clientes",
                "title": "Satisfação de Clientes",
                "icon": "⭐", 
                "type": "group",
                "expanded": False,
                "children": [
                    {
                        "id": "nps-geral",
                        "title": "NPS Geral",
                        "file": "nps_geral_dashboard.html",
                        "description": "Net Promoter Score consolidado"
                    },
                    {
                        "id": "satisfacao-produtos",
                        "title": "Satisfação por Produto",
                        "file": "satisfacao_produtos_dashboard.html",
                        "description": "Avaliação específica por linha de produto"
                    },
                    {
                        "id": "sugestoes-melhorias",
                        "title": "Sugestões e Melhorias",
                        "file": "sugestoes_melhorias_dashboard.html",
                        "description": "Feedback qualitativo dos clientes"
                    }
                ]
            },
            {
                "id": "pesquisa-colaboradores",
                "title": "Clima Organizacional",
                "icon": "👥",
                "type": "group", 
                "expanded": False,
                "children": [
                    {
                        "id": "engajamento",
                        "title": "Engajamento",
                        "file": "engajamento_dashboard.html",
                        "description": "Níveis de engajamento por área"
                    },
                    {
                        "id": "lideranca",
                        "title": "Avaliação de Liderança", 
                        "file": "lideranca_dashboard.html",
                        "description": "Feedback sobre gestores e líderes"
                    }
                ]
            },
            {
                "id": "relatorio-executivo",
                "title": "Relatório Executivo",
                "icon": "📋",
                "type": "file",
                "file": "relatorio_executivo_dashboard.html",
                "description": "Síntese executiva de todas as pesquisas"
            },
            {
                "id": "benchmarks",
                "title": "Benchmarks Setoriais",
                "icon": "📊",
                "type": "file", 
                "file": "benchmarks_dashboard.html",
                "description": "Comparações com indicadores do setor"
            }
        ]
    }

def create_readme():
    """Cria arquivo README com instruções"""
    readme_content = """# Dashboard Master - Opinião Informação Estratégica

## 📋 O que é?

O Dashboard Master é um sistema centralizado para organizar e navegar entre múltiplas análises SPSS em um só lugar. 

## 🚀 Como usar?

### 1. Estrutura dos Arquivos
```
pasta_projeto/
├── dashboard_master.html          # Dashboard principal
├── dashboard_manager.py           # Gerenciador de configuração
├── perfil_consumidor_dashboard.html
├── tendencias_mercado_dashboard.html
├── analise_concorrencia_dashboard.html
└── outros_arquivos_spss.html
```

### 2. Gerando Análises SPSS

1. Use o script SPSS normal para gerar seus arquivos HTML:
```bash
python criar_dashboard_melhorado.py dados.sav --vars "P1,P2,P3"
```

2. Renomeie o arquivo gerado para um nome descritivo:
```
dados_dashboard_melhorado.html → perfil_consumidor_dashboard.html
```

### 3. Configurando o Menu

Use o gerenciador para adicionar análises ao menu:
```bash
python dashboard_manager.py
```

**Opções do menu:**
- ➕ Adicionar análise: Conecta arquivo HTML ao menu
- 📁 Criar grupo: Organiza análises em categorias  
- 📋 Listar itens: Mostra estrutura atual
- 🌐 Gerar HTML: Cria dashboard atualizado

### 4. Exemplo de Uso Completo

```bash
# 1. Gerar análise do perfil do consumidor
python criar_dashboard_melhorado.py perfil_consumidor.sav \
    --vars "IDADE,SEXO,RENDA,ESCOLARIDADE" \
    --filters "REGIAO,CIDADE" \
    -o perfil_consumidor_dashboard.html

# 2. Configurar menu
python dashboard_manager.py
# Escolher: 1 (Adicionar análise)
# Nome: "Perfil do Consumidor"  
# Arquivo: "perfil_consumidor_dashboard.html"
# Grupo: "Pesquisas de Mercado"

# 3. Gerar dashboard master atualizado
# No menu escolher: 5 (Gerar HTML)

# 4. Abrir dashboard_master_generated.html no navegador
```

## 🎯 Vantagens

✅ **Organização**: Todos os relatórios em um só lugar  
✅ **Navegação**: Menu lateral intuitivo com grupos/subgrupos  
✅ **Responsivo**: Funciona em desktop, tablet e mobile  
✅ **Flexível**: Adicione/remova análises facilmente  
✅ **Visual**: Interface corporativa profissional  

## 📁 Estrutura de Pastas Recomendada

```
projeto_pesquisas/
├── dashboard_master.html
├── dashboard_manager.py
├── dados_brutos/
│   ├── perfil_consumidor.sav
│   ├── tendencias_mercado.sav
│   └── satisfacao_clientes.sav
├── scripts/
│   └── criar_dashboard_melhorado.py
└── analises/
    ├── perfil_consumidor_dashboard.html
    ├── tendencias_mercado_dashboard.html
    └── satisfacao_clientes_dashboard.html
```

## 🔧 Personalização

### Editando Configuração Diretamente

O arquivo `dashboard_config.json` pode ser editado manualmente:

```json
{
  "title": "Meu Dashboard Personalizado",
  "items": [
    {
      "id": "grupo-1",
      "title": "Meu Grupo", 
      "icon": "📊",
      "type": "group",
      "children": [
        {
          "id": "analise-1",
          "title": "Minha Análise",
          "file": "minha_analise.html"
        }
      ]
    }
  ]
}
```

### Ícones Disponíveis

Use emojis para os ícones:
- 📊 📈 📉 Análises/Gráficos
- 👥 👤 Pessoas/Demografia  
- ⭐ 💯 Satisfação/Qualidade
- 🏢 🏬 Negócios/Empresas
- 🎯 📋 Objetivos/Relatórios
- 📁 📂 Pastas/Organização

## ❓ Problemas Comuns

**Arquivo não encontrado:**
- Certifique-se que o arquivo HTML está na mesma pasta
- Verifique se o nome do arquivo está correto (sem espaços)

**Menu não aparece:**
- Execute `python dashboard_manager.py` para reconfigurar
- Verifique se o arquivo `dashboard_config.json` existe

**Layout quebrado:**
- Use navegadores modernos (Chrome, Firefox, Edge)
- Evite Internet Explorer

## 📞 Suporte

Para dúvidas sobre o Dashboard Master, consulte:
- Este README
- Comentários no código
- Exemplos na configuração padrão
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("📖 README.md criado com instruções completas")

def setup_quick():
    """Setup rápido com configuração de exemplo"""
    print("🚀 SETUP RÁPIDO DO DASHBOARD MASTER")
    print("=" * 50)
    
    # Cria configuração de exemplo
    config = create_sample_config()
    
    # Salva configuração
    with open("dashboard_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("✅ Configuração de exemplo criada: dashboard_config.json")
    
    # Cria README
    create_readme()
    
    # Verifica se dashboard_manager.py existe
    if not os.path.exists("dashboard_manager.py"):
        print("⚠️  dashboard_manager.py não encontrado na pasta atual")
        print("   Copie o arquivo dashboard_manager.py para esta pasta")
    
    # Cria HTML de demonstração
    demo_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Demonstração - Arquivo não configurado</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            padding: 40px; 
            background: #f8f9fa;
            color: #333;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 { color: #4A90E2; }
        .warning { 
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .steps {
            text-align: left;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Arquivo de Demonstração</h1>
        
        <div class="warning">
            <strong>⚠️ Este é um arquivo de exemplo!</strong><br>
            Para ver uma análise real, você precisa gerar arquivos HTML usando o script SPSS.
        </div>
        
        <div class="steps">
            <h3>Como substituir por análise real:</h3>
            <ol>
                <li>Gere um arquivo HTML com o script SPSS:
                    <br><code>python criar_dashboard_melhorado.py dados.sav --vars "VAR1,VAR2"</code>
                </li>
                <li>Renomeie o arquivo gerado para o nome configurado no menu</li>
                <li>Coloque na mesma pasta do Dashboard Master</li>
                <li>Recarregue o Dashboard Master</li>
            </ol>
        </div>
        
        <p><strong>Arquivo esperado:</strong> <span id="filename"></span></p>
        
        <script>
            // Mostra qual arquivo deveria estar aqui baseado na URL
            document.getElementById('filename').textContent = 
                window.location.pathname.split('/').pop();
        </script>
    </div>
</body>
</html>"""
    
    # Cria arquivos de demonstração para os exemplos
    demo_files = [
        "perfil_consumidor_dashboard.html",
        "tendencias_mercado_dashboard.html", 
        "analise_concorrencia_dashboard.html",
        "nps_geral_dashboard.html",
        "satisfacao_produtos_dashboard.html",
        "sugestoes_melhorias_dashboard.html",
        "engajamento_dashboard.html",
        "lideranca_dashboard.html",
        "relatorio_executivo_dashboard.html",
        "benchmarks_dashboard.html"
    ]
    
    for demo_file in demo_files:
        if not os.path.exists(demo_file):
            with open(demo_file, "w", encoding="utf-8") as f:
                f.write(demo_html)
    
    print(f"📄 {len(demo_files)} arquivos de demonstração criados")
    print("   (substitua pelos seus arquivos SPSS reais)")
    
    # Gera HTML final
    from dashboard_manager import DashboardManager
    manager = DashboardManager("dashboard_config.json")
    manager.generate_html("dashboard_master.html")
    
    print("\n🎉 SETUP CONCLUÍDO!")
    print("=" * 50)
    print("📁 Arquivos criados:")
    print("   • dashboard_master.html (dashboard principal)")
    print("   • dashboard_config.json (configuração)")
    print("   • README.md (instruções)")
    print("   • Arquivos de demonstração")
    print("\n📖 PRÓXIMOS PASSOS:")
    print("1. Abra dashboard_master.html no navegador")
    print("2. Gere seus arquivos SPSS reais") 
    print("3. Use dashboard_manager.py para personalizar")
    print("4. Substitua os arquivos de demonstração pelos reais")

if __name__ == "__main__":
    setup_quick()
