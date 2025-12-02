# Dashboard Master - Opinião Informação Estratégica

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
python criar_dashboard_melhorado.py perfil_consumidor.sav     --vars "IDADE,SEXO,RENDA,ESCOLARIDADE"     --filters "REGIAO,CIDADE"     -o perfil_consumidor_dashboard.html

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
