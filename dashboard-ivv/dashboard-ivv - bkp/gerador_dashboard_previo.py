#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Dashboard HTML para Análise Imobiliária com Controle de Acesso por Perfil
Versão 2.0 - Sistema de Permissões Integrado
"""

import argparse
import pandas as pd
import numpy as np
import json
import os
import sys
import unicodedata
from datetime import datetime
# Alguns ambientes (como servidores ou notebooks em modo headless) podem não ter tkinter instalado.
# Se a importação falhar, definimos tk e filedialog como None para evitar erro na importação.
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None
from typing import List, Dict, Any, Optional, Tuple

# Importa sistema de permissões
try:
    from user_permission_manager import UserPermissionManager, DataSanitizer
    PERMISSIONS_AVAILABLE = True
except ImportError:
    print("⚠️ Sistema de permissões não encontrado. Executando em modo básico.")
    UserPermissionManager = None
    DataSanitizer = None
    PERMISSIONS_AVAILABLE = False

# ==================== CONSTANTES ====================

# Colunas obrigatórias para dados residenciais
RESIDENTIAL_REQUIRED_COLS = [
    'ANO_MES', 'ORIGEM_RECURSOS', 'ESTAGIO_OBRA', 'OFERTA_VENDA', 
    'BAIRRO', 'AREA', 'QUANTIDADE', 'QTD_QUARTOS', 'QTD_ELEVADORES', 
    'QTD_GARAGEM', 'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2', 
    'AREA_QUANTIDADE', 'AREA_VALOR', 'AREA_QUANTIDADE_VALOR', 'EMPREENDIMENTO'
]

# Colunas obrigatórias para dados comerciais
COMMERCIAL_REQUIRED_COLS = [
    'ANO_MES', 'ORIGEM_RECURSOS', 'ESTAGIO_OBRA', 'OFERTA_VENDA', 
    'BAIRRO', 'AREA', 'QUANTIDADE', 'QTD_GARAGEM', 'QTD_ELEVADORES', 
    'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2', 'AREA_QUANTIDADE', 
    'AREA_VALOR', 'AREA_QUANTIDADE_VALOR', 'EMPREENDIMENTO'
]

# Faixas de valores para categorização
FAIXAS_VALOR = [
    (0, 350000, "< 350.000"),
    (350000, 500000, "350.000 – 499.999"),
    (500000, 700000, "500.000 – 699.999"),
    (700000, 1000000, "700.000 – 999.999"),
    (1000000, 2000000, "1.000.000 – 1.999.999"),
    (2000000, float('inf'), "≥ 2.000.000")
]

# Faixas de área para categorização (em m²)
FAIXAS_AREA = [
    (0, 40, "Até 40m²"),
    (41, 60, "41 a 60m²"),
    (61, 80, "61 a 80m²"),
    (81, 100, "81 a 100m²"),
    (101, 120, "101 a 120m²"),
    (121, 150, "121 a 150m²"),
    (151, 175, "151 a 175m²"),
    (176, 200, "176 a 200m²"),
    (201, float('inf'), "Mais de 200m²")
]

# Nomes dos meses abreviados
MESES_ABREV = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
]

# Mapeamento mês -> trimestre
TRIMESTRES = {
    1: '1T', 2: '1T', 3: '1T',
    4: '2T', 5: '2T', 6: '2T',
    7: '3T', 8: '3T', 9: '3T',
    10: '4T', 11: '4T', 12: '4T'
}

# Tipos de oferta/venda para filtros
OFERTA_LANCAMENTOS = ['OFERTADOS LANCAMENTOS']
OFERTA_DISPONIVEIS = ['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS']
VENDIDOS = ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS']
DISTRATO = ['DISTRATO']

# Sufixos a remover de nomes de empreendimentos
EMPREENDIMENTO_SUFFIXES = [
    r'\s+(Torre|Bloco|Torre de|Bloco de)\s+[A-Z]+$',
    r'\s+(Apartamento|Apto|Apt)\s*\d*$',
    r'\s+(Duplex|Cobertura|Penthouse)$',
    r'\s+(Fase|Etapa)\s*\d+$',
    r'\s+(I|II|III|IV|V|\d+)$',
    r'\s+[A-Z]$',
    r'\s+\d+$'
]

class LaunchDataManager:
    """
    Gerencia dados de lançamentos separando informações públicas e privadas
    VERSÃO 2: USA DIRETAMENTE get_projects_details para TUDO
    """
    
    def __init__(self, dashboard_generator):
        self.generator = dashboard_generator
    
    def get_public_launch_counts(self, df):
        """
        VERSÃO SIMPLIFICADA: USA DIRETAMENTE get_projects_details
        """
        if df is None or df.empty:
            return {
                "monthly_units": {}, "quarterly_units": {}, "yearly_units": {},
                "monthly_projects": {}, "quarterly_projects": {}, "yearly_projects": {}
            }
        
        # USAR DIRETAMENTE A FUNÇÃO QUE GERA O TXT
        projects_details = self.generator.get_projects_details(df)
        
        # CONTAGEM DE EMPREENDIMENTOS: simples len() da lista
        monthly_projects = {}
        monthly_units = {}
        
        for period, projects_list in projects_details.items():
            # Empreendimentos: tamanho da lista
            monthly_projects[period] = len(projects_list)
            
            # Unidades: somar do período (SEM tentar filtrar novamente)
            period_data = df[df['ANO_MES'] == period]
            period_launches = period_data[period_data['OFERTA_VENDA'] == 'OFERTADOS LANCAMENTOS']
            monthly_units[period] = int(period_launches['QUANTIDADE'].sum())
        
        # Agregar para trimestral e anual
        quarterly_units = self._aggregate_to_quarters(monthly_units)
        yearly_units = self._aggregate_to_years(monthly_units)
        quarterly_projects = self._aggregate_to_quarters(monthly_projects)
        yearly_projects = self._aggregate_to_years(monthly_projects)
        
        return {
            "monthly_units": monthly_units,
            "quarterly_units": quarterly_units,
            "yearly_units": yearly_units,
            "monthly_projects": monthly_projects,
            "quarterly_projects": quarterly_projects,
            "yearly_projects": yearly_projects
        }
    
    def _aggregate_to_quarters(self, monthly_data):
        """Agrega dados mensais para trimestral"""
        quarterly = {}
        for period, count in monthly_data.items():
            try:
                period_int = int(period)
                year = period_int // 100
                month = period_int % 100
                quarter = (month - 1) // 3 + 1
                key = f"{year}_{quarter}T"
                quarterly[key] = quarterly.get(key, 0) + int(count)
            except:
                continue
        return quarterly
    
    def _aggregate_to_years(self, monthly_data):
        """Agrega dados mensais para anual"""
        yearly = {}
        for period, count in monthly_data.items():
            try:
                period_int = int(period)
                year = str(period_int // 100)
                yearly[year] = yearly.get(year, 0) + int(count)
            except:
                continue
        return yearly
    
    def get_private_launch_details(self, df):
        """
        Retorna detalhes COMPLETOS para TXT privado
        Usa a função existente get_projects_details
        """
        return self.generator.get_projects_details(df)
    
    def generate_private_txt_report(self, details_data, output_file):
        """
        Gera relatório TXT com informações completas
        Usa a função existente aggregate_projects_to_years_with_list
        """
        return self.generator.aggregate_projects_to_years_with_list(details_data, output_file)

class DashboardGenerator:
    """
    Gerador de Dashboard HTML para Análise Imobiliária.
    
    Esta classe processa dados de planilhas Excel contendo informações do mercado
    imobiliário e gera um dashboard HTML interativo standalone (sem dependências
    externas) com visualizações, filtros e relatórios.
    
    Funcionalidades principais:
    - Carregamento de dados residenciais, comerciais e insights (INCC)
    - Processamento e agregação temporal (mensal, trimestral, anual)
    - Cálculo de métricas (IVV, vendas, lançamentos, ofertas, VGV, VGL)
    - Geração de HTML com JavaScript/CSS embutidos
    - Exportação de relatórios TXT de lançamentos
    - Sistema de autenticação simples
    - Exportação para PDF
    
    Attributes:
        residential_data: DataFrame com dados residenciais
        commercial_data: DataFrame com dados comerciais
        incc_data: DataFrame com dados do INCC
        residential_required_cols: Colunas obrigatórias para residencial
        commercial_required_cols: Colunas obrigatórias para comercial
    
    Example:
        >>> generator = DashboardGenerator()
        >>> generator.run("dados.xlsx", "dashboard.html")
    """
    
    def __init__(self, user_email: str = None, config_file: str = "user_profiles.json"):
        """
        Inicializa o gerador com configurações padrão e sistema de permissões.
        
        Args:
            user_email: Email do usuário autenticado (OAuth Google)
            config_file: Arquivo de configuração de usuários e permissões
        """
        self.residential_data: Optional[pd.DataFrame] = None
        self.commercial_data: Optional[pd.DataFrame] = None
        self.incc_data: Optional[pd.DataFrame] = None
        self.ipca_data: Optional[pd.DataFrame] = None          # NOVO
        self.selic_data: Optional[pd.DataFrame] = None         # NOVO
        self.juros_reais_data: Optional[pd.DataFrame] = None   # NOVO
        
        self.residential_required_cols = RESIDENTIAL_REQUIRED_COLS
        self.commercial_required_cols = COMMERCIAL_REQUIRED_COLS
        
        # Sistema de permissões
        self.permission_manager = None
        self.data_sanitizer = None
        self.user_authenticated = False
        
        if PERMISSIONS_AVAILABLE and user_email:
            try:
                self.permission_manager = UserPermissionManager(config_file)
                self.user_authenticated = self.permission_manager.authenticate_user(user_email)
                
                if self.user_authenticated:
                    self.data_sanitizer = DataSanitizer(self.permission_manager)
                    print(f"🔐 Sistema de permissões ativado para: {user_email}")
                    user_info = self.permission_manager.get_user_info()
                    print(f"   Perfil: {user_info['profile_name']}")
                else:
                    print(f"❌ Falha na autenticação para: {user_email}")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar sistema de permissões: {e}")
                print("   Executando em modo sem permissões.")
        elif not PERMISSIONS_AVAILABLE:
            print("⚠️ Sistema de permissões não disponível. Executando em modo básico.")
        else:
            print("ℹ️ Nenhum usuário especificado. Executando sem controle de acesso.")
        
        # Gerenciador de lançamentos
        self.launch_manager = LaunchDataManager(self)

    def load_permissions_config(self):
        """Carrega configurações de permissões do arquivo JSON"""
        try:
            with open('dashboard_permissions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Arquivo dashboard_permissions.json não encontrado. Usando configurações padrão.")
            # Configuração padrão se arquivo não existir
            return {
                'generated_at': datetime.now().isoformat(),
                'permissions': {
                    'admin': {
                        'menus': ['residencial', 'comercial', 'crosstabs', 'insights'],
                        'submenus': {
                            'residencial': ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
                            'comercial': ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
                            'crosstabs': ['oferta_quantidade','venda_quantidade','valor_ponderado_oferta','valor_ponderado_venda','oferta_m2','venda_m2'],
                            'insights': ['indicadores_economicos','correlacoes']
                        }
                    },
                    'manager': {
                        'menus': ['residencial', 'comercial'],
                        'submenus': {
                            'residencial': ['ivv','oferta','venda','vgl','vgv'],
                            'comercial': ['ivv','oferta','venda']
                        }
                    },
                    'analyst': {
                        'menus': ['residencial'],
                        'submenus': {
                            'residencial': ['ivv','oferta','venda']
                        }
                    },
                    'viewer': {
                        'menus': ['residencial'],
                        'submenus': {
                            'residencial': ['ivv']
                        }
                    }
                }
            }
        except Exception as e:
            print(f"❌ Erro ao carregar configurações: {e}")
            # Retorna configuração mínima em caso de erro
            return {
                'permissions': {
                    'admin': {'menus': ['residencial', 'comercial', 'crosstabs', 'insights']},
                    'manager': {'menus': ['residencial', 'comercial']},
                    'analyst': {'menus': ['residencial']},
                    'viewer': {'menus': ['residencial']}
                }
            }

    def get_user_by_profile(self, target_profile):
        """Encontra o primeiro usuário ativo com o perfil desejado"""
        try:
            with open('user_profiles.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            users = config.get('users', {})
            
            # Procura primeiro usuário ativo com o perfil
            for email, user_data in users.items():
                if (user_data.get('profile') == target_profile and 
                    user_data.get('active', False)):
                    print(f"👤 Encontrado usuário {target_profile}: {email}")
                    return email
            
            print(f"❌ Nenhum usuário ativo encontrado para perfil: {target_profile}")
            return None
            
        except Exception as e:
            print(f"❌ Erro ao consultar usuários: {e}")
            return None
  
    # ==================== FUNÇÕES AUXILIARES DE TEXTO ====================
    
    def normalize_string(self, text: Any) -> str:
        """
        Normaliza strings removendo acentos, espaços extras e caracteres especiais.
        
        Útil para comparações case-insensitive e accent-insensitive, especialmente
        para nomes de bairros e empreendimentos.
        
        Args:
            text: Texto a normalizar (pode ser string, número ou None)
            
        Returns:
            Texto normalizado em minúsculas sem acentos
            
        Example:
            >>> normalize_string("São Paulo  ")
            "sao paulo"
            >>> normalize_string(None)
            ""
        """
        if pd.isna(text) or text is None:
            return ''
        
        text = str(text).strip()
        normalized = unicodedata.normalize('NFD', text)
        without_accents = ''.join(
            c for c in normalized 
            if unicodedata.category(c) != 'Mn'
        )
        return without_accents


    def format_ano_mes(self, ano_mes: int) -> str:
        """
        Formata período AAAAMM para formato legível 'Mês/AAAA'.
        
        Args:
            ano_mes: Período no formato AAAAMM (ex: 202401 para Jan/2024)
            
        Returns:
            String formatada (ex: 'Jan/2024') ou 'N/A' se inválido
            
        Example:
            >>> format_ano_mes(202401)
            "Jan/2024"
            >>> format_ano_mes(202412)
            "Dez/2024"
        """
        if pd.isna(ano_mes):
            return "N/A"
        
        ano_mes_str = str(int(ano_mes)).zfill(6)
        ano = ano_mes_str[:4]
        mes_num = int(ano_mes_str[4:6])
        
        if 1 <= mes_num <= 12:
            mes_nome = MESES_ABREV[mes_num - 1]
            return f"{mes_nome}/{ano}"
        
        return "N/A"

    # ==================== FUNÇÕES DE CATEGORIZAÇÃO ====================
    
    def categorize_value(self, value: float) -> str:
        """
        Categoriza valor monetário em faixas predefinidas.
        
        Args:
            value: Valor em reais a categorizar
            
        Returns:
            String com a categoria da faixa de valor
            
        Example:
            >>> categorize_value(450000)
            "350.000 – 499.999"
        """
        if pd.isna(value):
            return "N/A"
        
        for min_val, max_val, label in FAIXAS_VALOR:
            if min_val <= value < max_val:
                return label
        
        return "N/A"
    
    def categorize_area(self, area: float) -> str:
        """
        Categoriza área em m² em faixas predefinidas.
        
        Args:
            area: Área em m² a categorizar
            
        Returns:
            String com a categoria da faixa de área
            
        Example:
            >>> categorize_area(75.5)
            "61 a 80m²"
        """
        if pd.isna(area):
            return "N/A"
        
        for min_area, max_area, label in FAIXAS_AREA:
            if min_area <= area <= max_area:
                return label
        
        return "N/A"
    
    def get_trimestre(self, mes: int) -> str:
        """
        Retorna o trimestre correspondente a um mês.
        
        Args:
            mes: Número do mês (1-12)
            
        Returns:
            String do trimestre ('1T', '2T', '3T', '4T') ou 'N/A'
            
        Example:
            >>> get_trimestre(5)
            "2T"
        """
        if pd.isna(mes):
            return "N/A"
        return TRIMESTRES.get(int(mes), "N/A")


    # ==================== PROCESSAMENTO DE EMPREENDIMENTOS ====================

    def extract_empreendimento_name(self, df):
        """
        Extrai e normaliza nome do empreendimento.
        
        VERSÃO CORRIGIDA: Inclui correções ortográficas e patterns para fases de projeto.
        
        Args:
            df: DataFrame com coluna 'EMPREENDIMENTO'
            
        Returns:
            DataFrame com coluna 'EMPREENDIMENTO_AGRUPADO' adicionada
        """
        df = df.copy()
        df['EMPREENDIMENTO_AGRUPADO'] = df['EMPREENDIMENTO'].fillna('N/A')
        
        # === CORREÇÕES ORTOGRÁFICAS CRÍTICAS ===
        # Aplicar ANTES da normalização geral
        df['EMPREENDIMENTO_AGRUPADO'] = df['EMPREENDIMENTO_AGRUPADO'].str.replace(
            'EMPPREENDIMENTO', 'EMPREENDIMENTO', case=False, regex=False
        ).str.replace(
            'EMPREEENDIMENTO', 'EMPREENDIMENTO', case=False, regex=False
        ).str.replace(
            'EMPRENDIMENTO', 'EMPREENDIMENTO', case=False, regex=False
        )
        
        # === REMOÇÃO DE PREFIXOS GENÉRICOS ===
        # Remover prefixos redundantes ANTES dos patterns principais
        df['EMPREENDIMENTO_AGRUPADO'] = df['EMPREENDIMENTO_AGRUPADO'].str.replace(
            r'^EMPREENDIMENTO\s+', '', regex=True, case=False
        ).str.replace(
            r'^RESIDENCIAL\s+', '', regex=True, case=False
        ).str.replace(
            r'^RES\s+', '', regex=True, case=False
        ).str.strip()
        
        # Normalizar: remover sufixos padronizados (BL A, TORRE 1, etc)
        patterns_to_remove = [
            r'\s+BL\s+[A-Z0-9]+',
            r'\s+BLOCO\s+[A-Z0-9]+', 
            r'\s+TORRE\s+[A-Z0-9]+',
            r'\s+TIPO\b',
            r'\s+APTO\s+[A-Z0-9]+',
            r'\s+APT\s+[A-Z0-9]+',
            r'\s+APARTAMENTO\s+[A-Z0-9]+',
            r'\s+SALA\s+[A-Z0-9]+',
            r'\s+LOJA\s+[A-Z0-9]+',
            r'\s+COBERTURA\b',
            r'\s+GARDEN\b',
            r'\s+DUPLEX\b',
            r'\s+TRIPLEX\b',
            r'\s+[0-9]+Q\b',                    
            r'\s+[0-9]+\s+QUARTOS?',           
            r'\s+COM\s+TERRAÇO',               
            r'\s+STUDIO\b',                    
            r'\s+LOFT\b',                      
            r'\s+[0-9]+\s+SUÍTES?\b',          
            r'\s+D[0-9]+\b',                   
            r'\s+C[0-9]+\b',                   
        ]
        
        # Criar coluna com termo principal (normalizado)
        df['TERMO_PRINCIPAL'] = df['EMPREENDIMENTO_AGRUPADO'].str.upper().str.strip()
        
        # Aplicar remoção de padrões
        for pattern in patterns_to_remove:
            df['TERMO_PRINCIPAL'] = df['TERMO_PRINCIPAL'].str.replace(
                pattern, '', regex=True, case=False
            ).str.strip()
        
        # Criar máscara de códigos sequenciais (EMP_123, etc)
        df['IS_SEQUENTIAL_CODE'] = df['TERMO_PRINCIPAL'].str.match(r'^EMP_\d+$', na=False)
        
        # Separar nomes reais dos códigos
        real_names_mask = ~df['IS_SEQUENTIAL_CODE'] & (df['TERMO_PRINCIPAL'] != 'N/A')
        
        if real_names_mask.any():
            # CORREÇÃO: NÃO agrupar por similaridade - confiar apenas na normalização
            # A tríade (EMPREENDIMENTO_AGRUPADO, EMPRESA, BAIRRO) será suficiente
            # para identificar unicidade
            df.loc[real_names_mask, 'EMPREENDIMENTO_AGRUPADO'] = (
                df.loc[real_names_mask, 'TERMO_PRINCIPAL']
            )
        
        # Limpar colunas auxiliares
        df = df.drop(['TERMO_PRINCIPAL', 'IS_SEQUENTIAL_CODE'], axis=1)
        
        return df

    def get_projects_details(self, df, period_col="ANO_MES"):
        """
        Retorna detalhes dos empreendimentos lançados por período.
        
        REGRA CORRIGIDA: Considera primeira aparição POR ANO (não histórica global).
        
        Args:
            df: DataFrame com dados
            period_col: Coluna de período
            
        Returns:
            Dict {AAAAMM: [(empreendimento, empresa, bairro), ...]}
        """
        if df is None or df.empty:
            return {}
        df2 = self.extract_empreendimento_name(df.copy())
        df2['QUANTIDADE'] = pd.to_numeric(df2.get('QUANTIDADE'), errors='coerce').fillna(0)
        df2[period_col] = pd.to_numeric(df2.get(period_col), errors='coerce').astype('Int64')
        mask = (
            (df2['OFERTA_VENDA'] == 'OFERTADOS LANCAMENTOS') &
            (df2['QUANTIDADE'] > 0) &
            (df2[period_col].notna())
        )
        cols = ['EMPREENDIMENTO_AGRUPADO', 'EMPRESA', 'BAIRRO', period_col]
        lanc = df2.loc[mask, cols].dropna(
            subset=['EMPREENDIMENTO_AGRUPADO', 'EMPRESA', 'BAIRRO', period_col]
        )
        lanc = lanc[lanc['EMPREENDIMENTO_AGRUPADO'] != 'N/A']
        if lanc.empty:
            return {}
        # CORREÇÃO: Ordenar por período para encontrar primeira aparição
        lanc = lanc.sort_values(period_col)
        
        # MUDANÇA PRINCIPAL: Adicionar coluna ANO para agrupar por ano
        lanc['ANO'] = lanc[period_col].astype(str).str[:4].astype(int)
        
        # CORREÇÃO: Remover duplicatas considerando primeira aparição POR ANO
        # Mantém apenas a primeira aparição de cada tríade em cada ano
        unique_historical = lanc.drop_duplicates(
            subset=['ANO', 'EMPREENDIMENTO_AGRUPADO', 'EMPRESA', 'BAIRRO'],
            keep='first'  # Mantém apenas a primeira aparição por ano
        )
        
        # Remover coluna auxiliar ANO
        unique_historical = unique_historical.drop('ANO', axis=1)
        
        # Monta lista por período
        details = (
            unique_historical
            .groupby(period_col, group_keys=False)
            [['EMPREENDIMENTO_AGRUPADO', 'EMPRESA', 'BAIRRO']]
            .apply(lambda g: list(map(tuple, g.values.tolist())))
            .to_dict()
        )
        # Normaliza chave
        details = {int(k): v for k, v in details.items()}
        
        return details

    def count_unique_projects(self, df: pd.DataFrame, period_col: str = "ANO_MES") -> Dict[int, int]:
        """
        Conta empreendimentos únicos lançados por período.
        
        REGRA CORRIGIDA: Considera apenas a PRIMEIRA aparição histórica de cada empreendimento.
        Empreendimentos faseados são contados apenas no primeiro lançamento.
        
        Args:
            df: DataFrame com dados
            period_col: Coluna de período (padrão: "ANO_MES")
            
        Returns:
            Dict {periodo: contagem} - Ex: {202101: 5, 202102: 3}
        """
        if df is None or df.empty:
            return {}
        
        # Obtém detalhes dos projetos (já com primeira aparição apenas)
        details = self.get_projects_details(df, period_col)
        
        # Conta quantos empreendimentos em cada período
        counts = {period: len(projects) for period, projects in details.items()}
        
        return counts


    # ==================== ANÁLISE DE LANÇAMENTOS ====================
    
    def analyze_launches_by_company_and_neighborhood_with_empreendimentos(
        self, 
        df: pd.DataFrame, 
        last_months: List[int]
    ) -> Dict[str, Any]:
        """
        Analisa lançamentos por empresa, bairro e empreendimento nos últimos meses.
        
        Args:
            df: DataFrame com dados de lançamentos
            last_months: Lista de períodos (AAAAMM) a considerar
            
        Returns:
            Dicionário com estrutura:
            {
                'by_company': {...},
                'by_neighborhood': {...},
                'by_empreendimento': {...},
                'total_launches': int
            }
        """
        df_with_empreendimentos = self.extract_empreendimento_name(df)
        
        # Filtrar lançamentos nos períodos especificados
        launches = df_with_empreendimentos[
            (df_with_empreendimentos['OFERTA_VENDA'] == 'OFERTADOS LANCAMENTOS') &
            (df_with_empreendimentos['ANO_MES'].isin(last_months)) &
            (df_with_empreendimentos['QUANTIDADE'] > 0)
        ].copy()

        if launches.empty:
            return {
                'by_company': {}, 
                'by_neighborhood': {}, 
                'by_empreendimento': {}, 
                'total_launches': 0
            }

        launches['ANO_MES_FORMATTED'] = launches['ANO_MES'].apply(
            self.format_ano_mes
        )
        launches['QUANTIDADE'] = pd.to_numeric(
            launches['QUANTIDADE'], 
            errors='coerce'
        ).fillna(0)

        # Análise por empresa
        by_company = {}
        for empresa in launches['EMPRESA'].dropna().unique():
            emp_df = launches[launches['EMPRESA'] == empresa]
            emps = [
                e for e in emp_df['EMPREENDIMENTO_AGRUPADO'].unique() 
                if e != 'N/A'
            ]
            
            by_company[empresa] = {
                'total_quantidade': emp_df['QUANTIDADE'].sum(),
                'por_mes': {},
                'bairros': list(emp_df['BAIRRO'].unique()),
                'empreendimentos': emps
            }
            
            for mes in emp_df['ANO_MES_FORMATTED'].unique():
                mes_df = emp_df[emp_df['ANO_MES_FORMATTED'] == mes]
                emps_mes = [
                    e for e in mes_df['EMPREENDIMENTO_AGRUPADO'].unique() 
                    if e != 'N/A'
                ]
                
                by_company[empresa]['por_mes'][mes] = {
                    'quantidade': mes_df['QUANTIDADE'].sum(),
                    'bairros': list(mes_df['BAIRRO'].unique()),
                    'empreendimentos': emps_mes
                }

        # Análise por bairro
        by_neighborhood = {}
        for bairro in launches['BAIRRO'].dropna().unique():
            bai_df = launches[launches['BAIRRO'] == bairro]
            emps = [
                e for e in bai_df['EMPREENDIMENTO_AGRUPADO'].unique() 
                if e != 'N/A'
            ]
            
            by_neighborhood[bairro] = {
                'total_quantidade': bai_df['QUANTIDADE'].sum(),
                'empresas': list(bai_df['EMPRESA'].unique()),
                'empreendimentos': emps,
                'por_mes': {}
            }
            
            for mes in bai_df['ANO_MES_FORMATTED'].unique():
                mes_df = bai_df[bai_df['ANO_MES_FORMATTED'] == mes]
                emps_mes = [
                    e for e in mes_df['EMPREENDIMENTO_AGRUPADO'].unique() 
                    if e != 'N/A'
                ]
                
                by_neighborhood[bairro]['por_mes'][mes] = {
                    'quantidade': mes_df['QUANTIDADE'].sum(),
                    'empresas': list(mes_df['EMPRESA'].unique()),
                    'empreendimentos': emps_mes
                }

        # Análise por empreendimento
        by_empreendimento = {}
        for emp in launches['EMPREENDIMENTO_AGRUPADO'].dropna().unique():
            if emp == 'N/A':
                continue
            
            emp_df = launches[launches['EMPREENDIMENTO_AGRUPADO'] == emp]
            
            by_empreendimento[emp] = {
                'total_quantidade': emp_df['QUANTIDADE'].sum(),
                'empresas': list(emp_df['EMPRESA'].unique()),
                'bairros': list(emp_df['BAIRRO'].unique()),
                'por_mes': {}
            }
            
            for mes in emp_df['ANO_MES_FORMATTED'].unique():
                mes_df = emp_df[emp_df['ANO_MES_FORMATTED'] == mes]
                
                by_empreendimento[emp]['por_mes'][mes] = {
                    'quantidade': mes_df['QUANTIDADE'].sum(),
                    'empresas': list(mes_df['EMPRESA'].unique()),
                    'bairros': list(mes_df['BAIRRO'].unique())
                }

        return {
            'by_company': by_company,
            'by_neighborhood': by_neighborhood,
            'by_empreendimento': by_empreendimento,
            'total_launches': launches['QUANTIDADE'].sum()
        }

    # ==================== CONTAGEM DE PROJETOS ÚNICOS ====================
    
    
    def aggregate_projects_to_quarters(self, 
                                      projects_monthly: Dict[int, int]
                                      ) -> Dict[str, int]:
        """
        Agrega contagem mensal de projetos para trimestral.
        
        Args:
            projects_monthly: Dicionário {periodo_mensal: contagem}
            
        Returns:
            Dicionário {'AAAA_NT': contagem} com agregação trimestral
            
        Example:
            >>> aggregate_projects_to_quarters({202401: 5, 202402: 3, 202403: 7})
            {'2024_1T': 15}
        """
        quarterly = {}
        
        for period, count in projects_monthly.items():
            try:
                period_int = int(float(period))
                year = period_int // 100
                month = period_int % 100
            except Exception:
                continue
            
            quarter = (month - 1) // 3 + 1
            key = f"{year}_{quarter}T"
            quarterly[key] = quarterly.get(key, 0) + int(count)
        
        return quarterly

    def aggregate_projects_to_years(self, 
                                    projects_monthly: Dict[int, int]
                                    ) -> Dict[str, int]:
        """
        Agrega contagem mensal de projetos para anual.
        
        Args:
            projects_monthly: Dicionário {periodo_mensal: contagem}
            
        Returns:
            Dicionário {'AAAA': contagem} com agregação anual
            
        Example:
            >>> aggregate_projects_to_years({202401: 5, 202402: 3})
            {'2024': 8}
        """
        yearly = {}
        
        for period, count in projects_monthly.items():
            try:
                period_int = int(float(period))
                year = str(period_int // 100)
            except Exception:
                continue
            
            yearly[year] = yearly.get(year, 0) + int(count)
        
        return yearly

    def aggregate_projects_to_years_with_list(
        self, 
        projects_monthly: Dict[int, List[Tuple]], 
        output_file: str = "lancamentos_por_ano.txt"
    ) -> Tuple[Dict[str, int], Dict[str, List]]:
        """
        Soma por ano e gera TXT com detalhes dos lançamentos.
        
        ATUALIZADO: Agora funciona com dados já filtrados pela primeira aparição.
        
        Args:
            projects_monthly: Dict {periodo: [(emp, empresa, bairro), ...]} - JÁ FILTRADO
            output_file: Caminho do arquivo TXT de saída
            
        Returns:
            Tupla (soma_anual, projetos_detalhados)
        """
        yearly_sum = {}
        yearly_projects = {}

        for period, projects in projects_monthly.items():
            try:
                period_int = int(float(period))
                year = str(period_int // 100)
                month = period_int % 100
            except Exception:
                continue

            yearly_sum.setdefault(year, 0)
            yearly_projects.setdefault(year, [])

            yearly_sum[year] += len(projects)

            for tup in projects:
                if isinstance(tup, (tuple, list)):
                    if len(tup) == 3:
                        empreendimento, empresa, bairro = tup
                    elif len(tup) == 2:
                        empreendimento, empresa = tup
                        bairro = "N/A"
                    else:
                        empreendimento = tup[0] if len(tup) > 0 else "N/A"
                        empresa = tup[1] if len(tup) > 1 else "N/A"
                        bairro = tup[2] if len(tup) > 2 else "N/A"
                else:
                    empreendimento, empresa, bairro = str(tup), "N/A", "N/A"

                yearly_projects[year].append(
                    (month, empresa, bairro, empreendimento)
                )

        # Escrever arquivo TXT
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== LANÇAMENTOS POR ANO ===\n")
            f.write("Regra: Cada empreendimento é contado quando o incorporador o insere no sistema como lançamento.\n")
            f.write("Fases posteriores são ignoradas.\n\n")
            
            for year in sorted(yearly_projects.keys()):
                f.write(f"Ano: {year}\n")
                f.write(f"Total lançamentos: {yearly_sum.get(year, 0)}\n")
                f.write("Empreendimentos Lançados:\n\n")
                
                for month, empresa, bairro, empreendimento in sorted(
                    yearly_projects[year], 
                    key=lambda x: (x[0], x[1], x[2], x[3])
                ):
                    f.write(f"  - {month:02d} | {empresa} | {bairro} | {empreendimento}\n")
                
                f.write("\n")

        return yearly_sum, yearly_projects
    
    
    # ==================== INTERFACE DE SELEÇÃO DE ARQUIVO ====================
    
    def select_input_file(self) -> str:
        """
        Abre diálogo para seleção do arquivo Excel de entrada.
        
        Returns:
            Caminho do arquivo selecionado ou string vazia se cancelado
        """
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo Excel de entrada",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        
        root.destroy()
        return file_path

    # ==================== DERIVAÇÃO DE CAMPOS ====================
    
    def derive_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deriva campos calculados no DataFrame (faixas, datas, trimestres).
        
        Args:
            df: DataFrame original com dados brutos
            
        Returns:
            DataFrame com campos derivados adicionados:
            - Faixa_Valor
            - Faixa_Area
            - ANO_MES_NUM
            - ANO
            - MES
            - TRIMESTRE
        """
        df = df.copy()
        
        # Aplicar categorização usando funções
        df['Faixa_Valor'] = df['AREA_VALOR'].apply(self.categorize_value)
        df['Faixa_Area'] = df['AREA'].apply(self.categorize_area)

        # Conversão segura de ANO_MES
        df['ANO_MES_NUM'] = pd.to_numeric(
            df.get('ANO_MES'), 
            errors='coerce'
        ).astype('Int64')

        # Deriva ANO e MES quando válido
        df['ANO'] = (df['ANO_MES_NUM'] // 100).astype('Int64')
        df['MES'] = (df['ANO_MES_NUM'] % 100).astype('Int64')

        # Aplicar trimestre usando função
        df['TRIMESTRE'] = df['MES'].apply(self.get_trimestre)

        return df

    # ==================== CARREGAMENTO DE DADOS ====================
    
    def load_data(self, file_path: str) -> bool:
        """
        Carrega dados das planilhas Excel.
        
        Carrega:
        - Sheet 0: Dados residenciais
        - Sheet 1: Dados comerciais (opcional)
        - Sheet 'INCC': Dados de insights INCC (opcional)
        - Sheet 'IPCA': Dados de IPCA (opcional)
        - Sheet 'SELIC': Dados de SELIC (opcional)
        - Sheet 'JUROS_REAIS': Dados de Juros Reais (opcional)
        """
        try:
            # Carregar planilha residencial (obrigatória)
            residential_df = pd.read_excel(file_path, sheet_name=0)
            
            # Carregar planilha comercial (opcional)
            try:
                commercial_df = pd.read_excel(file_path, sheet_name=1)
            except Exception:
                commercial_df = pd.DataFrame()
            
            # Carregar dados de Insights (opcional)
            try:
                incc_df = pd.read_excel(file_path, sheet_name='INCC')
            except Exception:
                incc_df = pd.DataFrame()
            
            # NOVO - Carregar dados de IPCA (opcional)
            try:
                ipca_df = pd.read_excel(file_path, sheet_name='IPCA')
            except Exception:
                ipca_df = pd.DataFrame()
            
            # NOVO - Carregar dados de SELIC (opcional)
            try:
                selic_df = pd.read_excel(file_path, sheet_name='SELIC')
            except Exception:
                selic_df = pd.DataFrame()
            
            # NOVO - Carregar dados de Juros Reais (opcional)
            try:
                juros_reais_df = pd.read_excel(file_path, sheet_name='JUROS_REAIS')
                
                # Processar dados de Juros Reais
                if not juros_reais_df.empty:
                    # Forçar conversão para numérico
                    juros_reais_df['VAR_MENSAL'] = pd.to_numeric(juros_reais_df['VAR_MENSAL'], errors='coerce')
                    
                    # Manter apenas colunas necessárias
                    juros_reais_df = juros_reais_df[['ANO_MES', 'VAR_MENSAL']]
                    
                    # Remover linhas com VAR_MENSAL vazio
                    juros_reais_df = juros_reais_df.dropna(subset=['VAR_MENSAL'])
                    
                    # Garantir que não há valores NaN
                    juros_reais_df = juros_reais_df.fillna(0)
                    
            except Exception as e:
                print(f"Erro ao carregar JUROS_REAIS: {e}")
                juros_reais_df = pd.DataFrame()
    
            # Processar e armazenar dados
            self.residential_data = self.derive_fields(residential_df)
            
            if not commercial_df.empty:
                self.commercial_data = self.derive_fields(commercial_df)
            else:
                self.commercial_data = pd.DataFrame()
            
            self.incc_data = incc_df
            self.ipca_data = ipca_df              # NOVO
            self.selic_data = selic_df            # NOVO
            self.juros_reais_data = juros_reais_df  # NOVO
                
            return True
            
        except Exception as e:
            print(f"Erro ao carregar arquivo: {e}")
            return False
    
    # ==================== PREPARAÇÃO DE DADOS PARA JSON ====================
    
    def prepare_data_for_json(self, df: pd.DataFrame) -> List[Dict]:
        """Prepara DataFrame para JSON com controle de acesso baseado em configurações"""
        if df.empty:
            return []
        
        df_json = df.copy()

        # Aplicar mascaramento baseado no perfil
        profile = getattr(self, '_profile_mode', 'admin')
        
        if profile != 'admin':
            # Para não-admins, aplicar mascaramento
            sensitive_columns = ['EMPRESA', 'EMPREENDIMENTO', 'EMPREENDIMENTO_AGRUPADO']
            
            for col in sensitive_columns:
                if col in df_json.columns:
                    if col == 'EMPRESA':
                        df_json[col] = 'EMPRESA PRIVADA'
                    elif col in ['EMPREENDIMENTO', 'EMPREENDIMENTO_AGRUPADO']:
                        df_json[col] = df_json[col].apply(lambda x: f'PROJETO {abs(hash(str(x))) % 1000:03d}' if pd.notna(x) else 'PROJETO 000')
        
        # Resto da função continua igual...
        # Normalização do bairro
        if 'BAIRRO' in df_json.columns:
            df_json['BAIRRO'] = (
                df_json['BAIRRO']
                .fillna('')
                .astype(str)
                .str.strip()
            )
            df_json = df_json[df_json['BAIRRO'] != '']
            df_json['BAIRRO_NORMALIZED'] = (
                df_json['BAIRRO'].apply(self.normalize_string)
            )

        # Garantir que ANO_MES seja inteiro (AAAAMM)
        if 'ANO_MES' in df_json.columns:
            df_json['ANO_MES'] = pd.to_numeric(
                df_json['ANO_MES'], 
                errors='coerce'
            )
            df_json['ANO_MES'] = df_json['ANO_MES'].dropna().astype(int)

        # Converter demais campos
        for col in df_json.columns:
            if col == 'ANO_MES':
                continue
            
            if pd.api.types.is_integer_dtype(df_json[col]):
                df_json[col] = (
                    pd.to_numeric(df_json[col], errors='coerce')
                    .fillna(0)
                    .astype(int)
                )
            elif pd.api.types.is_float_dtype(df_json[col]):
                df_json[col] = pd.to_numeric(df_json[col], errors='coerce')
            elif df_json[col].dtype == 'object':
                df_json[col] = df_json[col].astype(str)

        # Substituir NaN por None (compatível com JSON)
        df_json = df_json.where(pd.notnull(df_json), None)

        return df_json.to_dict('records')

    def prepare_crosstabs_data_for_json(self, df: pd.DataFrame) -> List[Dict]:
        """
        Prepara DataFrame especificamente para crosstabs com controle de acesso.
        
        Args:
            df: DataFrame a preparar
            
        Returns:
            Lista de dicionários prontos para JSON.dumps()
        """
        if df.empty:
            return []
        
        df_json = df.copy()

        # Aplicar sanitização baseada em permissões
        if self.data_sanitizer:
            df_json = self.data_sanitizer.sanitize_dataframe(df_json)
        else:
            # MODO LEGADO: Para crosstabs, manter todas as colunas mas anonimizar dados sensíveis
            if 'EMPRESA' in df_json.columns:
                df_json['EMPRESA'] = 'Empresa'  # Anonimizar
                
            if 'EMPREENDIMENTO' in df_json.columns:
                df_json['EMPREENDIMENTO'] = 'Empreendimento'  # Anonimizar
                
            if 'EMPREENDIMENTO_AGRUPADO' in df_json.columns:
                df_json['EMPREENDIMENTO_AGRUPADO'] = 'Empreendimento'  # Anonimizar

        # Normalização do bairro
        if 'BAIRRO' in df_json.columns:
            df_json['BAIRRO'] = (
                df_json['BAIRRO']
                .fillna('')
                .astype(str)
                .str.strip()
            )
            df_json = df_json[df_json['BAIRRO'] != '']
            df_json['BAIRRO_NORMALIZED'] = (
                df_json['BAIRRO'].apply(self.normalize_string)
            )

        # Garantir que ANO_MES seja inteiro (AAAAMM)
        if 'ANO_MES' in df_json.columns:
            df_json['ANO_MES'] = pd.to_numeric(
                df_json['ANO_MES'], 
                errors='coerce'
            )
            df_json['ANO_MES'] = df_json['ANO_MES'].dropna().astype(int)

        # Converter demais campos
        for col in df_json.columns:
            if col == 'ANO_MES':
                continue
            
            if pd.api.types.is_integer_dtype(df_json[col]):
                df_json[col] = (
                    pd.to_numeric(df_json[col], errors='coerce')
                    .fillna(0)
                    .astype(int)
                )
            elif pd.api.types.is_float_dtype(df_json[col]):
                df_json[col] = pd.to_numeric(df_json[col], errors='coerce')
            elif df_json[col].dtype == 'object':
                df_json[col] = df_json[col].astype(str)

        # Substituir NaN por None (compatível com JSON)
        df_json = df_json.where(pd.notnull(df_json), None)

        return df_json.to_dict('records')

    def get_data_periods(self, data: List[Dict]) -> set:
        """
        Extrai todos os períodos disponíveis nos dados.
        
        Args:
            data: Lista de dicionários com dados
            
        Returns:
            Set com períodos únicos (AAAAMM)
        """
        if not data:
            return set()
        
        periods = set()
        for row in data:
            val = row.get('ANO_MES')
            if val is None:
                continue
            
            try:
                periods.add(int(float(val)))
            except Exception:
                continue
        
        return periods

    def load_menu_permissions(self):
        """Carrega configurações de permissões de menu do arquivo JSON"""
        try:
            with open('dashboard_menu_permissions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Arquivo dashboard_menu_permissions.json não encontrado. Usando permissões padrão.")
            return None
        except Exception as e:
            print(f"❌ Erro ao carregar permissões de menu: {e}")
            return None
        
    def generate_html_template(self):
        """Gera template HTML com dados embedded e controle de menus por perfil"""
        
        # 🔹 Dados principais
        residential_json = json.dumps(self.prepare_data_for_json(self.residential_data), ensure_ascii=False)
        commercial_json = json.dumps(self.prepare_data_for_json(self.commercial_data), ensure_ascii=False)
        # 🔹 Dados para crosstabs (com todas as colunas necessárias)
        residential_crosstabs_json = json.dumps(self.prepare_crosstabs_data_for_json(self.residential_data), ensure_ascii=False)
        commercial_crosstabs_json = json.dumps(self.prepare_crosstabs_data_for_json(self.commercial_data), ensure_ascii=False)
        # 🔹 Contagem de lançamentos (para o dashboard)
                # 🔹 CORRIGIDO: Usar contagens separadas de unidades e empreendimentos
        residential_counts = self.launch_manager.get_public_launch_counts(self.residential_data)
        commercial_counts = self.launch_manager.get_public_launch_counts(self.commercial_data)
        # Consolidar contagens de UNIDADES (valores principais das tabelas)
        projects_count = {
            "residencial": residential_counts["monthly_units"],
            "residencial_quarterly": residential_counts["quarterly_units"],
            "residencial_yearly": residential_counts["yearly_units"],
            "comercial": commercial_counts["monthly_units"],
            "comercial_quarterly": commercial_counts["quarterly_units"],
            "comercial_yearly": commercial_counts["yearly_units"],
        }
        
        # Consolidar contagens de EMPREENDIMENTOS (para parênteses nas tabelas)
        projects_count_empreendimentos = {
            "residencial": residential_counts["monthly_projects"],
            "residencial_quarterly": residential_counts["quarterly_projects"],
            "residencial_yearly": residential_counts["yearly_projects"],
            "comercial": commercial_counts["monthly_projects"],
            "comercial_quarterly": commercial_counts["quarterly_projects"],
            "comercial_yearly": commercial_counts["yearly_projects"],
        }
        projects_count_json = json.dumps(projects_count, ensure_ascii=False)
        projects_count_empreendimentos_json = json.dumps(projects_count_empreendimentos, ensure_ascii=False)
        # 🔹 INCC
        incc_json = json.dumps(self.prepare_data_for_json(self.incc_data), ensure_ascii=False)
        ipca_json = json.dumps(self.prepare_data_for_json(self.ipca_data), ensure_ascii=False)          
        selic_json = json.dumps(self.prepare_data_for_json(self.selic_data), ensure_ascii=False)            
        juros_reais_json = json.dumps(self.prepare_data_for_json(self.juros_reais_data), ensure_ascii=False) 
        # 🔹 Obter períodos dos dados para determinar o último período disponível
        residential_periods = self.get_data_periods(self.prepare_data_for_json(self.residential_data))
        commercial_periods = self.get_data_periods(self.prepare_data_for_json(self.commercial_data))
        all_periods = residential_periods.union(commercial_periods)
        max_period = max(all_periods) if all_periods else 202409
        
        # 🔐 NOVO: Controle de menus por perfil
        profile = getattr(self, '_profile_mode', None)

        # Se não tem _profile_mode definido, pegar do usuário autenticado
        if not profile and hasattr(self, 'permission_manager') and self.permission_manager.current_user:
            profile = self.permission_manager.current_user.get('profile', 'admin')
        elif not profile:
            profile = 'admin'

        print(f"🔒 Aplicando configuração de menus para perfil: {profile}")

        # Carregar permissões de menu
        menu_permissions = self.load_menu_permissions()
        if menu_permissions and profile in menu_permissions.get('menu_permissions', {}):
            user_menu_config = menu_permissions['menu_permissions'][profile]
            
            # Debug detalhado
            print(f"✅ Configuração de menu carregada para {profile}:")
            for menu, submenus in user_menu_config.items():
                print(f"   📁 {menu}: {len(submenus)} submenus -> {submenus}")
        else:
            # Se não tem configuração específica, admin vê tudo, outros veem nada
            if profile == 'admin':
                user_menu_config = {
                    'residencial': ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
                    'comercial': ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
                    'crosstabs': ['ofertas_por_regiao','vendas_por_regiao','oferta_valor_pond_regiao','venda_valor_pond_regiao','oferta_m2_regiao','venda_m2_regiao','gastos_pos_entrega_regiao','gastos_categoria_regiao'],
                    'insights': ['indicadores_economicos','correlacoes']
                }
                print(f"⚠️ Usando configuração padrão para admin (todos os menus)")
            else:
                user_menu_config = {}
                print(f"⚠️ Nenhuma configuração encontrada para {profile} - sem menus visíveis")
        
        # ----------------------------------------------------------------------------
        # Antes de converter para JSON, normalizamos algumas chaves de submenu para
        # garantir que os códigos usados no JavaScript coincidam com os códigos
        # internos definidos em `viewCategories`. O arquivo de permissões pode
        # fornecer nomes de submenu com sufixos "_regiao" ou em português que não
        # coincidem exatamente com as strings internas (por exemplo,
        # "ofertas_por_regiao" em vez de "oferta_quantidade"). Abaixo está o
        # mapeamento de nomes externos para nomes internos.
        mapping_crosstabs = {
            'ofertas_por_regiao': 'oferta_quantidade',
            'vendas_por_regiao': 'venda_quantidade',
            'oferta_valor_pond_regiao': 'valor_ponderado_oferta',
            'venda_valor_pond_regiao': 'valor_ponderado_venda',
            'oferta_m2_regiao': 'oferta_m2',
            'venda_m2_regiao': 'venda_m2',
            'gastos_pos_entrega_regiao': 'gastos_pos_entrega',
            'gastos_categoria_regiao': 'gastos_por_categoria'
        }

        # Normalizar menus de crosstabs se existir tal chave
        normalized_menu_config = {}
        for menu_key, submenus in user_menu_config.items():
            # Copiar lista para evitar modificar a original
            normalized_subs = []
            for sub in submenus:
                # Se for crosstabs, aplicar mapping; caso contrário, manter
                if menu_key == 'crosstabs':
                    normalized_subs.append(mapping_crosstabs.get(sub, sub))
                else:
                    normalized_subs.append(sub)
            normalized_menu_config[menu_key] = normalized_subs

        # Converter permissões normalizadas para JSON para injetar no JavaScript
        menu_config_json = json.dumps({
            'profile': profile,
            'allowed_menus': list(normalized_menu_config.keys()),
            'menu_permissions': normalized_menu_config
        }, ensure_ascii=False)
        
        # 🔹 Montar HTML
        # Montar HTML (com ambas as contagens + configurações de menu)
        html_template = self.create_html_structure(
            residential_json, 
            commercial_json, 
            max_period,
            incc_json,
            ipca_json,           
            selic_json,          
            juros_reais_json,    
            projects_count_json,
            projects_count_empreendimentos_json,  # NOVO parâmetro
            residential_crosstabs_json,  # Dados específicos para crosstabs
            commercial_crosstabs_json,   # Dados específicos para crosstabs
            menu_config_json          # 🔐 NOVO: Configurações de menu
        )
        
        return html_template
    
    def create_html_structure(
        self, 
        residential_json, 
        commercial_json, 
        max_period, 
        incc_json, 
        ipca_json,           
        selic_json,
        juros_reais_json,
        projects_count_json,
        projects_count_empreendimentos_json,  
        residential_crosstabs_json,  
        commercial_crosstabs_json,
        menu_config_json,
        js_content="",   
        css_styles="", 
        html_body=""
    ):

        """Cria a estrutura HTML completa"""
        
        css_styles = """
        * {
            margin: 0; 
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #4A90E2 0%, #357ABD 100%);
            min-height: 100vh;
            color: #333;
            padding: 20px;
        }

        #dashboardContainer {
            display: none;
        }

        .header {
          background: rgba(255,255,255,0.95);
          border-radius: 10px;
          margin-bottom: 20px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.1);
          display: flex;
          align-items: center;
          justify-content: space-between; 
          padding: 20px;
        }

        .logo-container {
          flex: 0 0 auto; /* logo fixa na esquerda */
        }

        .header-center {
          flex: 1;                  
          text-align: center;       
        }

        .dashboard-title {
          font-size: 22px;
          font-weight: bold;
          margin-bottom: 12px;
          color: #1976D2;
        }

        .view-toggle {
          display: flex;
          gap: 12px;
          justify-content: center;
        }

        .logo-container {
            flex-shrink: 0;
        }

        .logo-container img {
            height: 80px;
            width: auto;
        }

        /* Estilos para informações do usuário */
        .user-info-container {
            background: rgba(74, 144, 226, 0.1);
            border-radius: 8px;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid rgba(74, 144, 226, 0.2);
        }

        .user-profile {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .user-icon {
            font-size: 16px;
            background: #4A90E2;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }

        .user-details {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .user-name {
            font-weight: 600;
            font-size: 12px;
            color: #333;
        }

        .user-role {
            font-size: 10px;
            color: #666;
            background: rgba(74, 144, 226, 0.1);
            padding: 2px 6px;
            border-radius: 10px;
            text-align: center;
        }

        .user-permissions {
            text-align: center;
            font-weight: 500;
        }

        .header-content {
            flex-grow: 1;
        }

        .header h1 {
            color: #4A90E2;
            font-size: 1.8rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 15px;
        }

        .view-toggle {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
            gap: 10px;
        }

        .view-btn {
            padding: 10px 25px;
            border: 2px solid #4A90E2;
            border-radius: 25px;
            background: rgba(255,255,255,0.9);
            color: #4A90E2;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .view-btn.active {
            background: #4A90E2;
            color: white;
        }

        .filters-container {
            background: #FFFFFF;
            border-radius: 0;
            padding: 15px 20px;
            margin-bottom: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-bottom: 1px solid #E5E5E5;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            z-index: 1500;
            padding-left: 300px;
            transition: padding-left 0.3s ease;
        }

        .filters-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .filters-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 0;
            align-items: center;
        }

        .filter-group {
            position: relative;
            min-width: 180px;
            flex: 0 0 auto;
        }

        .filter-label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: block;
        }

        .custom-dropdown {
            position: relative;
            width: 100%;
        }

        .dropdown-button {
            width: 100%;
            border: 1px solid #E5E5E5;
            border-radius: 4px;
            padding: 8px 10px;
            font-size: 12px;
            background: white;
            cursor: pointer;
            transition: border-color 0.3s ease;
            text-align: left;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .dropdown-button:hover {
            border-color: #4A90E2;
        }

        .dropdown-button.open {
            border-color: #4A90E2;
        }

        .dropdown-button .arrow {
            transition: transform 0.3s ease;
            font-size: 12px;
        }

        .dropdown-button.open .arrow {
            transform: rotate(180deg);
        }

        .dropdown-content {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #E5E5E5;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            z-index: 1000;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            margin-top: 2px;
        }

        .dropdown-content.show {
            display: block;
        }

        .dropdown-option {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .dropdown-option:hover {
            background-color: #F8F9FA;
        }

        .dropdown-option.select-all {
            background-color: #F8F9FA;
            border-bottom: 1px solid #E5E5E5;
            font-weight: 600;
            font-size: 12px;
        }

        .dropdown-option input[type="checkbox"] {
            margin-right: 8px;
            cursor: pointer;
        }

        .dropdown-option label {
            cursor: pointer;
            flex: 1;
            font-size: 12px;
        }

        .filter-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            flex: 0 0 auto;
        }

        .filter-btn {
            padding: 8px 20px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .apply-btn {
            background: #4A90E2;
            color: white;
        }

        .clear-btn {
            background: #f8f9fa;
            color: #666;
            border: 1px solid #ddd;
        }

        .filter-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }

        .tables-container {
            display: grid;
            gap: 20px;
            padding-top: 30px;
        }

        .table-card {
            background: rgba(255,255,255,0.98);
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow-x: auto;
            margin-bottom: 20px;
        }

        .table-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #4A90E2;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        .data-table th {
            background: #F8F9FA;
            padding: 8px 6px;
            text-align: center;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #E5E5E5;
            white-space: nowrap;
        }

        .data-table th:first-child {
            text-align: left;
            min-width: 60px;
        }

        .data-table td {
            padding: 6px 6px;
            border-bottom: 1px solid #F0F0F0;
            text-align: center;
        }

        .data-table td:first-child {
            text-align: left;
            font-weight: 500;
            color: #333;
        }

        .data-table tbody tr:hover {
            background-color: #F8F9FA;
        }

        .variation-row {
            background: #F8F9FA !important;
            font-weight: 600;
            border-top: 2px solid #E5E5E5;
        }

        .variation-row td {
            color: #666;
            font-size: 12px;
            padding: 8px;
        }

        .positive { color: #27AE60 !important; }
        .negative { color: #E74C3C !important; }
        .neutral { color: #95A5A6 !important; }

        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
            font-style: italic;
        }

        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
        }

        .variation-info {
            font-size: 12px;
            color: #333;
            margin-top: 10px;
            padding: 8px;
            background-color: transparent;
            border-radius: 4px;
            border-left: 3px solid #4A90E2;
        }

        .incomplete-note {
            font-size: 12px;
            color: #1976D2;
            margin-top: 10px;
            padding: 8px;
            background-color: #E3F2FD;
            border-radius: 4px;
        }

        .variation-info .positive {
            color: #27AE60 !important;
            font-weight: 600;
        }

        .variation-info .negative {
            color: #E74C3C !important;
            font-weight: 600;
        }

        .variation-info .neutral {
            color: #95A5A6 !important;
            font-weight: 600;
        }

        .footer {
            position: relative;
            bottom: auto;
            left: auto;
            right: auto;
            background: #FFFFFF;
            padding: 15px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #E5E5E5;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            margin-top: 40px;
            z-index: 10000;
        }

        /* ========= NOVO LAYOUT COM MENU LATERAL ========= */
        #dashboardContainer {
            display: flex;
            flex-direction: row;
        }
        .sidebar {
            background: #FFFFFF;
            border-right: 1px solid #E5E5E5;
            width: 280px;
            transition: width 0.3s ease;
            display: flex;
            flex-direction: column;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 2000;
            overflow-y: auto;
            box-shadow: 2px 0 8px rgba(0,0,0,0.15);
        }
        .sidebar.collapsed {
            width: 60px;
        }
        .sidebar .logo-container {
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            border-bottom: 1px solid #E5E5E5;
            flex-shrink: 0;
            min-height: 85px; /* Ajuste fino para alinhamento perfeito */
            box-sizing: border-box;
        }
        
        /* Ajustar padding da logo quando sidebar está retraído */
        .sidebar.collapsed .logo-container {
            padding: 10px 5px;
            min-height: 85px; /* Mantém alinhamento perfeito mesmo quando collapsed */
        }
        .sidebar ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .sidebar li {
            display: flex;
            align-items: center;
            cursor: pointer;
            padding: 10px 20px;
            color: #333;
            font-size: 14px;
            transition: background 0.2s ease;
            white-space: nowrap;
        }
        .sidebar li:hover {
            background: #F0F4F8;
        }
        .sidebar li.active {
            background: #E5EEF7;
            font-weight: 600;
        }
        .sidebar li .icon {
            margin-right: 10px;
            font-size: 18px;
            width: 24px;
            text-align: center;
        }
        .sidebar.collapsed li .text {
            display: none;
        }
        
        /* Esconder setas quando sidebar está retraído */
        .sidebar.collapsed .expand-icon {
            display: none;
        }
        
        /* Ícones das views ficam clicáveis quando sidebar retraída */
        .sidebar.collapsed .nav-item .icon {
            cursor: pointer;
            padding: 5px;
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        
        /* Hover effect nos ícones quando sidebar retraída */
        .sidebar.collapsed .nav-item .icon:hover {
            background-color: rgba(74, 144, 226, 0.1);
            transform: scale(1.1);
        }
        
        /* Tooltip para mostrar nome da view quando sidebar retraída */
        .sidebar.collapsed .nav-item {
            position: relative;
        }
        
        .sidebar.collapsed .nav-item:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            left: 70px;
            top: 50%;
            transform: translateY(-50%);
            background: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
            opacity: 0.9;
        }
        
        /* Logo no sidebar - Estados Normal e Retraído */
        .sidebar .logo-container img {
            height: 60px;
            width: auto;
            transition: all 0.3s ease;
            display: block;
            max-width: 100%;
            object-fit: contain; /* Mantém proporção */
        }
        
        /* Logo menor quando sidebar está retraído - mantém proporção */
        .sidebar.collapsed .logo-container img {
            height: 40px;
            width: auto;
            max-width: 40px; /* Limita largura para caber na sidebar retraída */
            object-fit: contain; /* Mantém proporção sem distorção */
        }
        
        /* Troca da imagem quando retraído - usando JavaScript para ser mais confiável */
        .sidebar .sidebar-toggle {
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-top: 1px solid #E5E5E5;
            flex-shrink: 0;
        }
        
        /* Menu principal (Residencial/Comercial) */
        .nav-main {
            border-bottom: 2px solid #E5E5E5;
            flex-shrink: 0;
        }
        
        .nav-main li {
            font-weight: 600;
            font-size: 15px;
            background: #FAFAFA;
            position: relative;
        }
        
        .nav-main li .expand-icon {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            transition: transform 0.2s ease;
            font-size: 12px;
        }
        
        .nav-main li.expanded .expand-icon {
            transform: translateY(-50%) rotate(90deg);
        }
        
        /* Submenus de categorias */
        .nav-categories {
            flex: 1;
            overflow-y: auto;
        }
        
        /* Container para submenus de cada setor */
        .submenu-container {
            display: none;
            background: #FFFFFF;
            border-left: 3px solid #4A90E2;
            margin-left: 10px;
        }
        
        .submenu-container.expanded {
            display: block;
        }
        
        .submenu-container li {
            padding: 12px 20px 12px 40px;
            font-size: 13px;
            font-weight: normal !important; /* Forçando remoção do negrito */
            background: #FFFFFF;
            border-bottom: 1px solid #F7F7F7;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .submenu-container li:hover {
            background: #F0F4F8;
            padding-left: 45px;
        }
        
        .submenu-container li.active {
            background: #E5EEF7;
            color: #4A90E2;
            font-weight: normal !important; /* Submenus ativos também sem negrito */
            border-left: 4px solid #4A90E2;
            padding-left: 41px;
        }
        .main-container {
            flex: 1;
            margin-left: 280px;
            width: calc(100% - 280px);
            transition: margin-left 0.3s ease, width 0.3s ease;
            display: flex;
            flex-direction: column;
            padding-top: 140px;
            /* Remover altura mínima fixa para permitir que o conteúdo cresça naturalmente e o sticky funcione corretamente */
        }
        .main-container.collapsed {
            margin-left: 60px;
            width: calc(100% - 60px);
        }
        
        /* Ajuste da barra de filtros */
        .filters-container {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            z-index: 1500;
            padding-left: 300px;
            transition: padding-left 0.3s ease;
        }
        
        .filters-container.collapsed {
            padding-left: 80px;
        }
        /* A barra de filtros fica sempre visível no topo da área principal */
        .filter-title {
            font-size: 16px;
            font-weight: 600;
            color: #1976D2;
            margin-bottom: 0;
            text-transform: uppercase;
        }

        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .export-btn {
            background-color: #1976d2;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .export-btn:hover {
            background-color: #1565c0;
        }

        /* INSIGHTS */
        .insights-container {
            display: grid;
            gap: 15px;
        }
        
        .insight-card {
            background: rgba(255,255,255,0.98);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow: visible;
        }
        
        .insight-title {
            color: #4A90E2;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .insight-description {
            color: #666;
            font-size: 12px;
            margin-bottom: 15px;
            line-height: 1.4;
        }
        
        .insight-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 12px;
        }
        
        .metric-box {
            background: #F8F9FA;
            border-radius: 8px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            border-left: 4px solid #4A90E2;
        }
        
        .metric-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        
        .metric-value {
            font-size: 22px;
            font-weight: 700;
            color: #333;
        }
        
        .metric-value.positive {
            color: #27AE60;
        }
        
        .metric-value.negative {
            color: #E74C3C;
        }
        
        .metric-period {
            font-size: 9px;
            color: #999;
        }
        
        .insight-note {
            font-size: 12px;
            color: #999;
            font-style: italic;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #E5E5E5;
        }
        
        .insight-subtitle {
            font-size: 13px;
            color: #555;
            margin: 6px 0 12px 0;
        }
        
        /* Gráfico - Desktop */
        .chart-wrapper {
            background: #fff;
            border: 1px solid #E5E5E5;
            border-radius: 10px;
            padding: 16px;
            margin-top: 12px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .chart-wrapper canvas {
            width: 100% !important;
            height: auto !important;
            max-height: 300px;
        }

        .table-note {
            font-size: 12px;
            color: #777;
            margin-top: 6px;
        }

        @media (max-width: 768px) {
            body {
                padding: 15px;
            }

            .dashboard-container {
                padding: 15px !important;
                padding-bottom: 100px !important;
            }
            
            .header {
                flex-direction: column;
                padding: 15px;
                margin-bottom: 15px;
            }
            
            .logo-container {
                margin-bottom: 10px;
            }
            
            .logo-container img {
                height: 60px;
                width: auto;
            }

            .header h1 {
                font-size: 1.2rem;
                margin-bottom: 10px;
            }
            
            .view-toggle {
                gap: 8px;
            }
            
            .view-btn {
                padding: 8px 16px;
                font-size: 13px;
            }
            
            .filters-container {
                padding: 12px 15px;
                margin-bottom: 0;
                position: relative;
                padding-left: 15px;
                width: 100%;
                left: 0;
                right: 0;
            }
            
            .filters-header {
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
                margin-bottom: 10px;
            }
            
            .filters-grid {
                flex-direction: column;
                gap: 15px;
                align-items: stretch;
            }
            
            .filter-actions {
                justify-content: center;
            }
            
            .filter-btn {
                padding: 9px 18px;
                font-size: 12px;
            }
            
            .table-card {
                padding: 15px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                margin-bottom: 15px;
            }

            .data-table {
                font-size: 10px;
                min-width: 650px;
                border-collapse: collapse;
                width: 100%;
            }

            .data-table th,
            .data-table td {
                padding: 6px 4px;
                text-align: left;
                white-space: nowrap;
            }
            
            /* INSIGHTS MOBILE - AJUSTES COMPACTOS */
            .insights-container {
                gap: 12px;              /* REDUZA de 15px para 12px */
            }
            
            .insight-card {
                padding: 12px;          /* REDUZA de 15px para 12px */
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }

            .insight-title {
                font-size: 14px;        /* REDUZA de 16px para 14px */
                margin-bottom: 6px;     /* REDUZA de 8px para 6px */
            }
            
            .insight-description {
                font-size: 11px;        /* REDUZA de 12px para 11px */
                margin-bottom: 12px;    /* REDUZA de 15px para 12px */
            }
            
            .insight-metrics {
                grid-template-columns: 1fr;
                gap: 10px;              /* REDUZA de 12px para 10px */
            }
            
            .metric-box {
                padding: 10px;          /* REDUZA de 12px para 10px */
                gap: 3px;               /* REDUZA de 4px para 3px */
            }
            
            .metric-label {
                font-size: 9px;         /* REDUZA de 10px para 9px */
            }
            
            .metric-value {
                font-size: 18px;        /* REDUZA de 22px para 18px */
            }
            
            .metric-period {
                font-size: 8px;         /* REDUZA de 9px para 8px */
            }
            
            .insight-note {
                font-size: 9px;         /* REDUZA de 10px para 9px */
                margin-top: 8px;        /* REDUZA de 10px para 8px */
                padding-top: 8px;       /* REDUZA de 10px para 8px */
            }
            
            /* Gráfico - ocupa largura total com scroll */
            .chart-wrapper {
                min-width: 600px;
                margin: 12px 0;
            }

            .chart-wrapper canvas {
                width: 100% !important;
                height: auto !important;
                max-height: 250px;
            }

            /* Ajuste de responsividade para tabelas e gráficos em Insights */
            .insight-card .data-table {
                font-size: 10px;
                min-width: 650px;
            }

            .insight-card .data-table th,
            .insight-card .data-table td {
                padding: 6px 4px;
            }

            .insight-card table {
                display: block;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                white-space: nowrap;
            }

            .insight-card .chart-wrapper {
                min-width: 600px;
                margin: 12px 0;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
            
            .footer {
                font-size: 10px;
                padding: 10px;
            }
        }
        """

        # HTML body content
        html_body = f"""
<!-- 🔹 Dashboard -->
<div id="dashboardContainer" style="display: block;">
    <div class="sidebar" id="sidebar">
        <div class="logo-container">
            <img src="https://raw.githubusercontent.com/aag1974/dashboard-ivv/main/logo.png" alt="Logo Opiniao" />
        </div>
        
        <!-- Informações do usuário -->
        <div class="user-info-container" id="userInfo" style="{'display: block;' if self.user_authenticated else 'display: none;'}">
            <div class="user-profile">
                <span class="user-icon">👤</span>
                <div class="user-details">
                    <span class="user-name" id="userName">
                        {self.permission_manager.get_user_info()['name'] if self.user_authenticated else 'Usuário'}
                    </span>
                    <span class="user-role" id="userRole">
                        {self.permission_manager.get_user_info()['profile_name'] if self.user_authenticated else 'Básico'}
                    </span>
                </div>
            </div>
            <div class="user-permissions" id="userPermissions" style="font-size: 10px; color: #666; margin-top: 5px;">
                {'🔓 Acesso Completo' if self.user_authenticated and self.permission_manager.has_permission('view_company_details') else '🔒 Acesso Restrito'}
            </div>
        </div>
        <ul class="nav-main">
            <li class="nav-item active" onclick="handleViewClick('residencial', event)" data-view="residencial" data-tooltip="Residencial">
                <span class="icon">🏠</span><span class="text">Residencial</span>
                <span class="expand-icon">▶</span>
            </li>
            <div class="submenu-container" id="submenu-residencial">
                <!-- Submenus residencial serão inseridos aqui -->
            </div>
            <li class="nav-item" onclick="handleViewClick('comercial', event)" data-view="comercial" data-tooltip="Comercial">
                <span class="icon">🏢</span><span class="text">Comercial</span>
                <span class="expand-icon">▶</span>
            </li>
            <div class="submenu-container" id="submenu-comercial">
                <!-- Submenus comercial serão inseridos aqui -->
            </div>
            <li class="nav-item" onclick="handleViewClick('crosstabs', event)" data-view="crosstabs" data-tooltip="Crosstabs">
                <span class="icon">📊</span><span class="text">Crosstabs</span>
                <span class="expand-icon">▶</span>
            </li>
            <div class="submenu-container" id="submenu-crosstabs">
                <!-- Submenus crosstabs serão inseridos aqui -->
            </div>
            <li class="nav-item" onclick="handleViewClick('insights', event)" data-view="insights" data-tooltip="Insights">
                <span class="icon">💡</span><span class="text">Insights</span>
                <span class="expand-icon">▶</span>
            </li>
            <div class="submenu-container" id="submenu-insights">
                <!-- Submenus insights serão inseridos aqui -->
            </div>
        </ul>
        
        <ul class="nav-categories" id="categoryNav">
            <!-- Para crosstabs e insights -->
        </ul>
        <div class="sidebar-toggle" onclick="toggleSidebar()">⇔</div>
    </div>
    <div class="main-container" id="mainContainer">
        <div class="filters-container">
            <div class="filters-header">
                <h2 class="filter-title">FILTROS DE SELEÇÃO</h2>
                <div class="filter-actions">
                    <button class="filter-btn apply-btn" onclick="applyFilters()">Aplicar Filtros</button>
                    <button class="filter-btn clear-btn" onclick="clearFilters()">Limpar Filtros</button>
                </div>
            </div>
            <div class="filters-grid">
                <div class="filter-group" id="faixaValorGroup">
                    <label class="filter-label">Faixa de Valor</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('faixaValor')">
                            <span id="faixaValorText">Todos</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="faixaValorContent">
                            <div class="dropdown-option select-all">
                                <input type="checkbox" onchange="selectAllOptions('faixaValor')">
                                <label>Selecionar Todos</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="< 350.000" onchange="updateDropdownText('faixaValor')">
                                <label>< 350.000</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="350.000 – 499.999" onchange="updateDropdownText('faixaValor')">
                                <label>350.000 – 499.999</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="500.000 – 699.999" onchange="updateDropdownText('faixaValor')">
                                <label>500.000 – 699.999</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="700.000 – 999.999" onchange="updateDropdownText('faixaValor')">
                                <label>700.000 – 999.999</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="1.000.000 – 1.999.999" onchange="updateDropdownText('faixaValor')">
                                <label>1.000.000 – 1.999.999</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="≥ 2.000.000" onchange="updateDropdownText('faixaValor')">
                                <label>≥ 2.000.000</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="filter-group" id="periodoGroup" style="display: none;">
                    <label class="filter-label">Período (Ano/Mês)</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('periodo')">
                            <span id="periodoText">Período mais recente</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="periodoContent">
                            <!-- Será populado dinamicamente -->
                        </div>
                    </div>
                </div>
                <div class="filter-group" id="faixaAreaGroup">
                    <label class="filter-label">Área Privativa</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('faixaArea')">
                            <span id="faixaAreaText">Todos</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="faixaAreaContent">
                            <div class="dropdown-option select-all">
                                <input type="checkbox" onchange="selectAllOptions('faixaArea')">
                                <label>Selecionar Todos</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="Até 40m²" onchange="updateDropdownText('faixaArea')">
                                <label>Até 40m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="41 a 60m²" onchange="updateDropdownText('faixaArea')">
                                <label>41 a 60m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="61 a 80m²" onchange="updateDropdownText('faixaArea')">
                                <label>61 a 80m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="81 a 100m²" onchange="updateDropdownText('faixaArea')">
                                <label>81 a 100m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="101 a 120m²" onchange="updateDropdownText('faixaArea')">
                                <label>101 a 120m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="121 a 150m²" onchange="updateDropdownText('faixaArea')">
                                <label>121 a 150m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="151 a 175m²" onchange="updateDropdownText('faixaArea')">
                                <label>151 a 175m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="176 a 200m²" onchange="updateDropdownText('faixaArea')">
                                <label>176 a 200m²</label>
                            </div>
                            <div class="dropdown-option">
                                <input type="checkbox" value="Mais de 200m²" onchange="updateDropdownText('faixaArea')">
                                <label>Mais de 200m²</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="filter-group" id="estagioObraGroup">
                    <label class="filter-label">Estágio da Obra</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('estagioObra')">
                            <span id="estagioObraText">Todos</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="estagioObraContent">
                        </div>
                    </div>
                </div>
                <div class="filter-group" id="bairroGroup">
                    <label class="filter-label">Região Administrativa</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('bairro')">
                            <span id="bairroText">Todos</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="bairroContent">
                        </div>
                    </div>
                </div>
                <div class="filter-group" id="quartosGroup">
                    <label class="filter-label">Número de Quartos</label>
                    <div class="custom-dropdown">
                        <div class="dropdown-button" onclick="toggleDropdown('quartos')">
                            <span id="quartosText">Todos</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="dropdown-content" id="quartosContent">
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div id="tablesContainer"></div>
        <div id="crossTablesContainer" style="display:none;"></div>
        <footer class="footer">
          Elaborado por <a href="https://www.opiniao.inf.br" target="_blank" style="color:#1976D2; text-decoration:none;">
            Opinião Informação Estratégica
          </a>. Reprodução Proibida.
        </footer>
    </div>
</div>
        """



        
        # JavaScript content - usando uma abordagem mais segura
        js_content = self.create_javascript_content(max_period)
        
        # Montar HTML completo
        full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DASHBOARD PESQUISA IVV</title>
    <style>{css_styles}</style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    {html_body}
    <script>
        // Dados do dashboard
        const rawData = {{
            residencial: {residential_json},
            comercial: {commercial_json}
        }};
        // Dados específicos para crosstabs (com todas as colunas necessárias)
        const crossTabsData = {{
            residencial: {residential_crosstabs_json},
            comercial: {commercial_crosstabs_json}
        }};
        const projectsCount = {projects_count_json};
        const projectsCountEmpreendimentos = {projects_count_empreendimentos_json};

        // 🔍 Dados de Insights (SELIC, IPCA, Juros Reais, INCC)
        // Estas séries são utilizadas na view "Insights" para montar os cartões de indicadores econômicos
        const insightsData = {{
            selic: {selic_json},
            ipca: {ipca_json},
            jurosReais: {juros_reais_json},
            incc: {incc_json}
        }};
        // Também expõe os dados de insights no objeto global "window" para evitar problemas de escopo
        window.insightsData = insightsData;
        
        // 🔐 Configurações de menu do usuário
        const menuConfig = {menu_config_json};
        const userProfile = menuConfig.profile;
        const allowedMenus = menuConfig.allowed_menus;
        const menuPermissions = menuConfig.menu_permissions;

        // Último período disponível nos dados (ano/mês como número inteiro)
        // Define a constante maxDataPeriod para ser usada nas funções de data do dashboard.
        const maxDataPeriod = {max_period};
        // Disponibiliza o valor no objeto global para evitar erros de escopo em outras funções
        window.maxDataPeriod = maxDataPeriod;
        
        console.log('👤 Perfil do usuário:', userProfile);
        console.log('🔒 Menus permitidos:', allowedMenus);
        console.log('📋 Permissões detalhadas:', menuPermissions);
        
        // Função para ocultar menus não permitidos
        function applyMenuPermissions() {{
            // Nova implementação: esconde menus e submenus usando data attributes
            console.log('🔒 Aplicando permissões de menu (nova lógica)...');
            console.log('Perfil:', userProfile);
            console.log('Menus permitidos:', allowedMenus);
            console.log('Permissões de submenus:', menuPermissions);
            if (userProfile !== 'admin') {{
                // Seleciona todos os itens de menu principal (li.nav-item) dentro da lista principal
                const mainMenuItems = document.querySelectorAll('.nav-main > li.nav-item');
                mainMenuItems.forEach(item => {{
                    const menuKey = item.getAttribute('data-view');
                    // Se o menu principal não for permitido, esconda-o e seu contêiner de submenus
                    if (!allowedMenus.includes(menuKey)) {{
                        item.style.display = 'none';
                        const submenuContainer = document.getElementById('submenu-' + menuKey);
                        if (submenuContainer) {{
                            submenuContainer.style.display = 'none';
                        }}
                    }} else {{
                        // Se o menu está permitido, verificar os submenus
                        const allowedSub = menuPermissions[menuKey] || [];
                        const submenuContainer = document.getElementById('submenu-' + menuKey);
                        if (submenuContainer) {{
                            const subItems = submenuContainer.querySelectorAll('li[data-category]');
                            subItems.forEach(li => {{
                                const category = li.getAttribute('data-category');
                                if (!allowedSub.includes(category)) {{
                                    li.style.display = 'none';
                                }}
                            }});
                        }}
                    }}
                }});
            }} else {{
                console.log('👑 Perfil admin - todos os menus e submenus visíveis');
            }}
        }}
        
        // Aplicar permissões quando página carrega
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('📄 Página carregada, aplicando permissões...');
            applyMenuPermissions();
        }});
        
        {js_content}
    </script>
</body>
</html>
"""

        return full_html
                        
    def create_javascript_content(self, max_period):
        """Cria o conteúdo JavaScript de forma segura"""
        
        js_code = r"""
        let currentView = 'residencial';
        let currentCategory = null; // Categoria ativa atualmente
        let expandedMenus = { residencial: true, comercial: false, crosstabs: false, insights: false }; // Residencial expandido por padrão
        
        // Mapeamento de categorias por view
        const viewCategories = {
            residencial: ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
            comercial: ['ivv','oferta','venda','lancamentos','oferta_m2','venda_m2','valor_ponderado_oferta','valor_ponderado_venda','vgl','vgv','distratos'],
            crosstabs: ['oferta_quantidade','venda_quantidade','valor_ponderado_oferta','valor_ponderado_venda','oferta_m2','venda_m2','gastos_pos_entrega','gastos_por_categoria'],
            insights: ['indicadores_economicos','correlacoes']
        };
        // Nomes amigáveis para categorias
        const friendlyNames = {
            ivv: 'IVV',
            oferta: 'Oferta',
            venda: 'Venda',
            lancamentos: 'Lançamentos',
            oferta_quantidade: 'Ofertas por Região',
            venda_quantidade: 'Vendas por Região',
            oferta_m2: 'Oferta em m²',
            venda_m2: 'Venda em m²',
            valor_ponderado_oferta: 'Oferta Valor Ponderado',
            valor_ponderado_venda: 'Venda Valor Ponderado',
            vgl: 'VGL',
            vgv: 'VGV',
            distratos: 'Distratos',
            indicadores_economicos: 'Indicadores Econômicos',
            correlacoes: 'Correlações',
            gastos_pos_entrega: 'Gastos Pós-entrega por Região',
            gastos_por_categoria: 'Gastos Pós-entrega por Categoria',
        };
        
        // Nomes específicos para crosstabs (incluem "p/ Região")
        const friendlyNamesCrosstabs = {
            oferta_quantidade: 'Ofertas por Região',
            venda_quantidade: 'Vendas por Região',
            valor_ponderado_oferta: 'Oferta Valor Pond. p/ Região',
            valor_ponderado_venda: 'Venda Valor Pond. p/ Região',
            oferta_m2: 'Oferta em m² p/ Região',
            venda_m2: 'Venda em m² p/ Região',
            gastos_pos_entrega: 'Gastos Pós-entrega p/ Região',
            gastos_por_categoria: 'Gastos p/ Categoria e Região'
        };
        
        // Função para obter nome amigável baseado na view
        function getFriendlyName(cat) {
            if (currentView === 'crosstabs' && friendlyNamesCrosstabs[cat]) {
                return friendlyNamesCrosstabs[cat];
            }
            return friendlyNames[cat] || cat;
        }
        
        // Função para detectar períodos incompletos

        function getCurrentPeriodInfo() {
            // Usar o último período dos dados reais, não a data atual do sistema
            const maxPeriodStr = maxDataPeriod.toString().padStart(6, '0');
            const maxYear = parseInt(maxPeriodStr.substring(0, 4));
            const maxMonth = parseInt(maxPeriodStr.substring(4, 6));
            
            // Determinar trimestre do último período nos dados
            let maxQuarter;
            if (maxMonth >= 1 && maxMonth <= 3) maxQuarter = 1;
            else if (maxMonth >= 4 && maxMonth <= 6) maxQuarter = 2;
            else if (maxMonth >= 7 && maxMonth <= 9) maxQuarter = 3;
            else maxQuarter = 4;
            
            return {
                maxYear: maxYear,
                maxMonth: maxMonth,
                maxQuarter: maxQuarter,
                maxPeriod: maxDataPeriod,
                maxQuarterKey: maxYear + '_' + maxQuarter + 'T'
            };
        }

        function isIncompleteQuarter(quarterKey, currentInfo) {
            const parts = quarterKey.split('_');
            const year = parseInt(parts[0]);
            const quarter = parseInt(parts[1].replace('T', ''));
            
            // Se o ano é anterior ao último ano com dados, trimestre está completo
            if (year < currentInfo.maxYear) return false;
            
            // Se o ano é posterior ao último ano com dados, trimestre não iniciou
            if (year > currentInfo.maxYear) return false;
            
            // Mesmo ano - verificar status do trimestre
            if (quarter < currentInfo.maxQuarter) {
                // Trimestre anterior ao atual - deve estar completo
                return false;
            } else if (quarter > currentInfo.maxQuarter) {
                // Trimestre posterior ao atual - ainda não iniciou
                return false;
            } else {
                // Mesmo trimestre - verificar se está completo
                const quarterEndMonths = [3, 6, 9, 12];
                const expectedEndMonth = quarterEndMonths[quarter - 1];
                
                // Se ainda não chegou ao último mês do trimestre, está incompleto
                return currentInfo.maxMonth < expectedEndMonth;
            }
        }

        function isIncompleteYear(year, currentInfo) {
            const yearInt = parseInt(year);
            if (yearInt < currentInfo.maxYear) return false;
            if (yearInt > currentInfo.maxYear) return true;
            
            // Mesmo ano - verificar se dezembro foi alcançado
            return currentInfo.maxMonth < 12;
        }

        function isIncompleteMonthPeriod(period, currentInfo) {
            return period > currentInfo.maxPeriod;
        }
        function hasCompleteDataForPeriod(data, period) {
            // Verifica se há dados reais (não zeros) para o período
            return data && data[period] !== undefined && data[period] !== null && data[period] > 0;
        }
        
        function normalizeString(str) {
            if (!str || typeof str !== 'string') return '';
            
            return str.toString()
                     .trim()
                     .normalize('NFD')
                     .replace(/[\\u0300-\\u036f]/g, '');
        }
        
        let bairroSystem = {
            availableBairros: [],
            selectedBairros: [],
            bairroMapping: {},
            
            extractUniqueBairros: function(data) {
                const bairrosRaw = data
                    .map(function(row) { return row.BAIRRO; })
                    .filter(function(bairro) { return bairro && bairro.toString().trim() !== ''; });
                
                const bairroMap = new Map();
                
                bairrosRaw.forEach(function(bairro) {
                    const original = bairro.toString().trim();
                    const normalized = normalizeString(original);
                    
                    if (!bairroMap.has(normalized)) {
                        bairroMap.set(normalized, original);
                    }
                });
                
                const bairrosUnicos = Array.from(bairroMap.values());
                
                bairrosUnicos.sort(function(a, b) {
                    return a.localeCompare(b, 'pt-BR', { 
                        sensitivity: 'base', 
                        numeric: true 
                    });
                });
                
                this.bairroMapping = {};
                const self = this;
                bairroMap.forEach(function(original, normalized) {
                    self.bairroMapping[normalized] = original;
                });
                
                return bairrosUnicos;
            },
            
            populateDropdown: function(data) {
                this.availableBairros = this.extractUniqueBairros(data);
                
                const bairroContent = document.getElementById('bairroContent');
                if (!bairroContent) return;
                
                bairroContent.innerHTML = '';
                
                const selectAllDiv = document.createElement('div');
                selectAllDiv.className = 'dropdown-option select-all';
                selectAllDiv.innerHTML = '<input type="checkbox" id="bairroSelectAll"><label for="bairroSelectAll">Selecionar Todos</label>';
                bairroContent.appendChild(selectAllDiv);
                
                document.getElementById('bairroSelectAll').onchange = function() {
                    bairroSystem.selectAll(this.checked);
                };
                
                const self = this;
                this.availableBairros.forEach(function(bairro, index) {
                    const optionDiv = document.createElement('div');
                    optionDiv.className = 'dropdown-option';
                    
                    const checkboxId = 'bairro_' + index;
                    optionDiv.innerHTML = '<input type="checkbox" id="' + checkboxId + '" value="' + bairro + '"><label for="' + checkboxId + '">' + bairro + '</label>';
                    bairroContent.appendChild(optionDiv);
                    
                    document.getElementById(checkboxId).onchange = function() {
                        self.updateSelection();
                    };
                });
                
                this.updateDisplayText();
            },
            
            selectAll: function(checked) {
                const checkboxes = document.querySelectorAll('#bairroContent input[type="checkbox"]:not(#bairroSelectAll)');
                checkboxes.forEach(function(cb) {
                    cb.checked = checked;
                });
                
                this.updateSelection();
            },
            
            updateSelection: function() {
                const checkboxes = document.querySelectorAll('#bairroContent input[type="checkbox"]:not(#bairroSelectAll)');
                const checkedBoxes = document.querySelectorAll('#bairroContent input[type="checkbox"]:not(#bairroSelectAll):checked');
                
                this.selectedBairros = Array.from(checkedBoxes).map(function(cb) { return cb.value; });
                
                const selectAllCheckbox = document.getElementById('bairroSelectAll');
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = checkedBoxes.length === checkboxes.length && checkboxes.length > 0;
                }
                
                this.updateDisplayText();
            },
            
            updateDisplayText: function() {
                const textElement = document.getElementById('bairroText');
                if (!textElement) return;
                
                if (this.selectedBairros.length === 0) {
                    textElement.textContent = 'Todos';
                } else if (this.selectedBairros.length === 1) {
                    textElement.textContent = this.selectedBairros[0];
                } else if (this.selectedBairros.length === this.availableBairros.length) {
                    textElement.textContent = 'Todos';
                } else {
                    textElement.textContent = this.selectedBairros.length + ' selecionados';
                }
            },
            
            clear: function() {
                const checkboxes = document.querySelectorAll('#bairroContent input[type="checkbox"]');
                checkboxes.forEach(function(cb) {
                    cb.checked = false;
                });
                
                this.selectedBairros = [];
                this.updateDisplayText();
            },
            
            filterData: function(data) {
                if (this.selectedBairros.length === 0) {
                    return data;
                }
                
                const selectedNormalized = this.selectedBairros.map(function(b) { return normalizeString(b); });
                const self = this;
                
                const filteredData = data.filter(function(row) {
                    const rowBairro = row.BAIRRO ? row.BAIRRO.toString().trim() : '';
                    const rowBairroNormalized = normalizeString(rowBairro);
                    
                    const matchOriginal = self.selectedBairros.includes(rowBairro);
                    const matchNormalized = selectedNormalized.includes(rowBairroNormalized);
                    
                    return matchOriginal || matchNormalized;
                });
                
                return filteredData;
            }
        };

        function toggleDropdown(filterId) {
            const button = event.currentTarget;
            const content = document.getElementById(filterId + 'Content');
            
            document.querySelectorAll('.dropdown-content').forEach(function(dropdown) {
                if (dropdown !== content) {
                    dropdown.classList.remove('show');
                }
            });
            document.querySelectorAll('.dropdown-button').forEach(function(btn) {
                if (btn !== button) {
                    btn.classList.remove('open');
                }
            });
            
            content.classList.toggle('show');
            button.classList.toggle('open');
        }

        function selectAllOptions(filterId) {
            const content = document.getElementById(filterId + 'Content');
            const selectAllCheckbox = content.querySelector('.select-all input');
            const checkboxes = content.querySelectorAll('.dropdown-option:not(.select-all) input[type="checkbox"]');
            
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllCheckbox.checked;
            });
            
            updateDropdownText(filterId);
        }

        function updateDropdownText(filterId) {
            const content = document.getElementById(filterId + 'Content');
            const textElement = document.getElementById(filterId + 'Text');
            const selectAllCheckbox = content.querySelector('.select-all input');
            const checkboxes = content.querySelectorAll('.dropdown-option:not(.select-all) input[type="checkbox"]');
            const checkedBoxes = content.querySelectorAll('.dropdown-option:not(.select-all) input[type="checkbox"]:checked');
            
            if (checkedBoxes.length === 0) {
                textElement.textContent = 'Todos';
                if (selectAllCheckbox) selectAllCheckbox.checked = false;
            } else if (checkedBoxes.length === 1) {
                textElement.textContent = checkedBoxes[0].nextElementSibling.textContent;
                if (selectAllCheckbox) selectAllCheckbox.checked = false;
            } else if (checkedBoxes.length === checkboxes.length) {
                textElement.textContent = 'Todos';
                if (selectAllCheckbox) selectAllCheckbox.checked = true;
            } else {
                textElement.textContent = checkedBoxes.length + ' selecionados';
                if (selectAllCheckbox) selectAllCheckbox.checked = false;
            }
        }

        function buildEconomicIndicatorsMonthly(selicRows, ipcaRows, jurosReaisRows, inccRows) {
            // Função auxiliar para processar cada série
            function processSeries(rows, seriesName, useAcum12 = false) {
                if (!rows || rows.length === 0) return { labels: [], values: [], monthsOrdered: [] };
                
                const ordered = sortByAnoMesAsc(rows, r => r.ANO_MES || 0);
                const labels = [];
                const values = [];
                const monthsOrdered = [];
                
                ordered.forEach(r => {
                    if (r.ANO_MES) {
                        const value = useAcum12 ? r.ACUM_12_MESES : r.VAR_MENSAL;
                        
                        if (value !== null && value !== undefined) {
                            labels.push(formatMesAbrev(r.ANO_MES));
                            values.push(value);
                            monthsOrdered.push(r.ANO_MES);
                        }
                    }
                });
                
                return { labels, values, monthsOrdered };
            }
            
            const selic = processSeries(selicRows, 'SELIC', false);
            const ipca = processSeries(ipcaRows, 'IPCA', true);
            const jurosReais = processSeries(jurosReaisRows, 'Juros Reais', false);
            const incc = processSeries(inccRows, 'INCC', true); // ACUM_12_MESES
            
            // Encontrar períodos comuns
            const setS = new Set(selic.monthsOrdered);
            const setI = new Set(ipca.monthsOrdered);
            const setJ = new Set(jurosReais.monthsOrdered);
            const setIncc = new Set(incc.monthsOrdered);
            
            const commonMonths = selic.monthsOrdered.filter(m => 
                setI.has(m) && setJ.has(m) && setIncc.has(m)
            );
            
            if (commonMonths.length === 0) {
                return { labels: [], selic: [], ipca: [], jurosReais: [], incc: [] };
            }
            
            const labels = commonMonths.map(formatMesAbrev);
            const selicData = commonMonths.map(m => selic.values[selic.monthsOrdered.indexOf(m)]);
            const ipcaData = commonMonths.map(m => ipca.values[ipca.monthsOrdered.indexOf(m)]);
            const jurosReaisData = commonMonths.map(m => jurosReais.values[jurosReais.monthsOrdered.indexOf(m)]);
            const inccData = commonMonths.map(m => incc.values[incc.monthsOrdered.indexOf(m)]);
            
            return { 
                labels, 
                periods: commonMonths,
                selic: selicData, 
                ipca: ipcaData, 
                jurosReais: jurosReaisData,
                incc: inccData
            };
        }

        // Função para normalizar dados para base 100
        function normalizeToBase100(values) {
            if (!values || values.length === 0) return [];
            
            // Encontrar primeiro valor válido (> 0) como base
            const baseValue = values.find(v => v > 0);
            if (!baseValue) return values;
            
            return values.map(v => v > 0 ? (v / baseValue) * 100 : null);
        }
        
        // Função para calcular média móvel
        function calculateRollingAverage(values, window) {
            if (!values || values.length === 0) return [];
            
            const result = [];
            for (let i = 0; i < values.length; i++) {
                if (i < window - 1) {
                    // Primeiros valores = originais (até completar janela)
                    result.push(values[i]);
                } else {
                    // Calcular média dos últimos 'window' valores
                    const slice = values.slice(i - window + 1, i + 1);
                    const validValues = slice.filter(v => v !== null && v !== undefined);
                    if (validValues.length > 0) {
                        const avg = validValues.reduce((sum, val) => sum + val, 0) / validValues.length;
                        result.push(avg);
                    } else {
                        result.push(values[i]);
                    }
                }
            }
            return result;
        }

        // Calcular variáveis secundárias do mercado imobiliário
        function calculateSecondaryVariables(residentialData) {
            const monthlyData = {};
            
            residentialData.forEach(row => {
                const period = row.ANO_MES;
                if (!period) return;
                
                if (!monthlyData[period]) {
                    monthlyData[period] = {
                        vendas: 0,
                        ofertas: 0,
                        lancamentos: 0,
                        vgl: 0,
                        vgv: 0,
                        ofertasUnidades: 0
                    };
                }
                
                const quantidade = row.QUANTIDADE || 0;
                const valor = row.AREA_QUANTIDADE_VALOR || 0;
                
                if (row.OFERTA_VENDA === 'VENDIDOS' || row.OFERTA_VENDA === 'VENDIDOS - LANCADOS E VENDIDOS') {
                    monthlyData[period].vendas += quantidade;
                    monthlyData[period].vgv += valor;
                } else if (row.OFERTA_VENDA === 'OFERTADOS DISPONIVEIS' || row.OFERTA_VENDA === 'OFERTADOS LANCAMENTOS') {
                    monthlyData[period].ofertas += quantidade;
                    monthlyData[period].ofertasUnidades += quantidade;
                }
                
                if (row.OFERTA_VENDA === 'OFERTADOS LANCAMENTOS') {
                    monthlyData[period].lancamentos += quantidade;
                    monthlyData[period].vgl += valor;
                }
            });
            
            // Calcular IVV
            const ivv = {};
            Object.keys(monthlyData).forEach(period => {
                const data = monthlyData[period];
                ivv[period] = data.ofertasUnidades > 0 ? (data.vendas / data.ofertasUnidades) * 100 : 0;
            });
            
            // Converter para arrays ordenados
            const periods = Object.keys(monthlyData).map(p => parseInt(p)).sort((a, b) => a - b);
            
            // Arrays com dados mensais originais
            const monthlyArrays = {
                ivv: periods.map(p => ivv[p] || 0),
                oferta: periods.map(p => monthlyData[p].ofertas),
                venda: periods.map(p => monthlyData[p].vendas),
                vgl: periods.map(p => monthlyData[p].vgl / 1000000), // Converter para milhões
                vgv: periods.map(p => monthlyData[p].vgv / 1000000), // Converter para milhões
                lancamentos: periods.map(p => monthlyData[p].lancamentos)
            };
            
            // Aplicar base 100 aos dados mensais
            const base100Arrays = {
                ivv: normalizeToBase100(monthlyArrays.ivv),
                oferta: normalizeToBase100(monthlyArrays.oferta),
                venda: normalizeToBase100(monthlyArrays.venda),
                vgl: normalizeToBase100(monthlyArrays.vgl),
                vgv: normalizeToBase100(monthlyArrays.vgv),
                lancamentos: normalizeToBase100(monthlyArrays.lancamentos)
            };
            
            // Aplicar médias móveis aos dados base 100
            const smoothedArrays = {
                ivv: calculateRollingAverage(base100Arrays.ivv, 3),
                oferta: calculateRollingAverage(base100Arrays.oferta, 3),
                venda: calculateRollingAverage(base100Arrays.venda, 3),
                vgl: calculateRollingAverage(base100Arrays.vgl, 3),
                vgv: calculateRollingAverage(base100Arrays.vgv, 3),
                lancamentos: calculateRollingAverage(base100Arrays.lancamentos, 3)
            };
            
            // Debug logs
            console.log('📊 Variáveis de Mercado - Transformações aplicadas:');
            console.log('📈 Dados originais (primeiros 5):', {
                ivv: monthlyArrays.ivv.slice(0, 5),
                oferta: monthlyArrays.oferta.slice(0, 5),
                venda: monthlyArrays.venda.slice(0, 5)
            });
            console.log('💯 Base 100 (primeiros 5):', {
                ivv: base100Arrays.ivv.slice(0, 5),
                oferta: base100Arrays.oferta.slice(0, 5),
                venda: base100Arrays.venda.slice(0, 5)
            });
            console.log('📊 Suavizados (primeiros 5):', {
                ivv: smoothedArrays.ivv.slice(0, 5),
                oferta: smoothedArrays.oferta.slice(0, 5),
                venda: smoothedArrays.venda.slice(0, 5)
            });
            
            return {
                periods: periods,
                labels: periods.map(formatMesAbrev),
                
                // Dados finais: base 100 + suavizados (para correlações e gráfico)
                ivv: smoothedArrays.ivv,
                oferta: smoothedArrays.oferta,
                venda: smoothedArrays.venda,
                vgl: smoothedArrays.vgl,
                vgv: smoothedArrays.vgv,
                lancamentos: smoothedArrays.lancamentos,
                
                // Dados originais (manter para debug/comparação)
                ivv_original: monthlyArrays.ivv,
                oferta_original: monthlyArrays.oferta,
                venda_original: monthlyArrays.venda,
                vgl_original: monthlyArrays.vgl,
                vgv_original: monthlyArrays.vgv,
                lancamentos_original: monthlyArrays.lancamentos
            };
        }

        // Função utilitária: alinha duas séries temporais e aplica uma janela móvel
        function alignAndWindow(periodsA, seriesA, periodsB, seriesB, window = null) {
            console.log('alignAndWindow chamada:', {
                periodsA: periodsA?.length || 0,
                seriesA: seriesA?.length || 0,
                periodsB: periodsB?.length || 0,
                seriesB: seriesB?.length || 0,
                window
            });
            
            if (!periodsA || !seriesA || !periodsB || !seriesB) {
                console.log('alignAndWindow: dados faltando');
                return { arrA: [], arrB: [] };
            }

            // Alinha os períodos (ex: 202301, 202302, etc.)
            const commonPeriods = periodsA.filter(p => periodsB.includes(p));
            console.log('alignAndWindow: períodos comuns:', commonPeriods.length);
            
            if (commonPeriods.length === 0) {
                console.log('alignAndWindow: nenhum período comum');
                return { arrA: [], arrB: [] };
            }

            // Extrai apenas os valores dos períodos comuns
            const arrA = [];
            const arrB = [];
            commonPeriods.forEach(p => {
                const idxA = periodsA.indexOf(p);
                const idxB = periodsB.indexOf(p);
                const valA = parseFloat(seriesA[idxA]);
                const valB = parseFloat(seriesB[idxB]);
                if (!isNaN(valA) && !isNaN(valB)) {
                    arrA.push(valA);
                    arrB.push(valB);
                }
            });

            console.log('alignAndWindow: valores válidos encontrados:', arrA.length);

            // Aplica janela móvel (mantém últimos N registros) OU usa série completa
            if (window && arrA.length > window) {
                console.log('alignAndWindow: aplicando janela de', window, 'meses');
                return {
                    arrA: arrA.slice(arrA.length - window),
                    arrB: arrB.slice(arrB.length - window)
                };
            }

            console.log('alignAndWindow: usando série completa:', arrA.length, 'pontos');
            return { arrA, arrB };
        }


        // Função para calcular o coeficiente de correlação de Pearson entre dois vetores
        function pearson(x, y) {
            if (!x || !y || x.length !== y.length || x.length === 0) return null;

            const n = x.length;
            const meanX = x.reduce((a, b) => a + b, 0) / n;
            const meanY = y.reduce((a, b) => a + b, 0) / n;

            let num = 0;
            let denX = 0;
            let denY = 0;

            for (let i = 0; i < n; i++) {
                const dx = x[i] - meanX;
                const dy = y[i] - meanY;
                num += dx * dy;
                denX += dx * dx;
                denY += dy * dy;
            }

            const den = Math.sqrt(denX * denY);
            if (den === 0) return null;
            return num / den;
        }


        function renderCorrelationNarrative(containerId, variableKey, variableLabel, economicData, secondaryVars) {
            console.log('🎯 renderCorrelationNarrative INICIADA');
            console.log('📊 Parâmetros recebidos:', { containerId, variableKey, variableLabel });
            
            const el = document.getElementById(containerId);
            if (!el) {
                console.log('❌ Elemento não encontrado:', containerId);
                return;
            }
            
            console.log('✅ Elemento encontrado:', containerId);
            console.log('renderCorrelationNarrative chamada:', { containerId, variableKey, variableLabel });
            console.log('economicData:', economicData);
            console.log('secondaryVars:', secondaryVars);

            const econVars = [
                { key: 'selic', label: 'SELIC' },
                { key: 'ipca', label: 'IPCA 12m' },
                { key: 'jurosReais', label: 'Juros Reais' },
                { key: 'incc', label: 'INCC 12m' }
            ];

            const { periods: pB, [variableKey]: seriesB } = secondaryVars;
            console.log('Dados da variável selecionada:', { variableKey, seriesB, periods: pB });
            
            if (!seriesB) {
                el.innerHTML = `<em>Dados indisponíveis para ${variableLabel}.</em>`;
                console.log('Série B indisponível para:', variableKey);
                return;
            }

            const lines = [];

            econVars.forEach(ev => {
                const seriesA = economicData[ev.key];
                console.log(`Processando ${ev.key}:`, seriesA);
                
                const { arrA, arrB } = alignAndWindow(
                    economicData.periods,
                    seriesA,
                    pB,
                    seriesB
                    // Usar série completa disponível
                );
                
                console.log(`Após alinhamento ${ev.key}:`, { arrA: arrA.length, arrB: arrB.length });
                
                const r = pearson(arrA, arrB);
                console.log(`Correlação ${ev.key} vs ${variableKey}:`, r, `(${arrA.length} pontos analisados)`);
                
                if (r === null || isNaN(r)) {
                    console.log(`Correlação inválida para ${ev.key}: ${r}`);
                    return;
                }

                const color = r >= 0.5 ? 'green' : r >= 0.3 ? 'orange' : r > 0.1 ? '#666' : r <= -0.5 ? 'red' : r <= -0.3 ? 'orange' : r < -0.1 ? '#666' : '#999';
                const tendencia =
                    r >= 0.5 ? 'forte positiva' :
                    r >= 0.3 ? 'moderada positiva' :
                    r > 0.1 ? 'fraca positiva' :
                    r <= -0.5 ? 'forte negativa' :
                    r <= -0.3 ? 'moderada negativa' :
                    r < -0.1 ? 'fraca negativa' : 'neutra';
                const txt = `<li><strong style="color:${color};">${ev.label}:</strong> correlação ${tendencia} (${r.toFixed(2).replace('.', ',')})</li>`;
                lines.push(txt);
            });

            console.log('Lines geradas:', lines);

            if (!lines.length) {
                el.innerHTML = `<em>Não há correlações suficientes para ${variableLabel} no período analisado.</em>`;
                return;
            }

            el.innerHTML = `
                <p><strong>${variableLabel}</strong> apresenta as seguintes correlações com os indicadores econômicos (série temporal completa):</p>
                <ul style="margin-left:16px; padding-left:0;">${lines.join('')}</ul>
                <p style="font-size:12px; color:#777;">Coeficientes de Pearson calculados sobre todo o período disponível — positivos indicam que as variáveis tendem a se mover na mesma direção; negativos, em direções opostas.</p>
            `;
        }
        

        // Toggle de variáveis secundárias
        function toggleSecondaryVariable(variable) {
            if (!window.economicChart) return;
            
            const datasetLabels = {
                'ivv': 'IVV - Base 100 (MM 3m)',
                'oferta': 'OFERTA - Base 100 (MM 3m)',
                'venda': 'VENDA - Base 100 (MM 3m)',
                'vgl': 'VGL - Base 100 (MM 3m)',
                'vgv': 'VGV - Base 100 (MM 3m)',
                'lancamentos': 'Lançamentos - Base 100 (MM 3m)'
            };
            
            const targetLabel = datasetLabels[variable];
            const chart = window.economicChart;
            
            chart.data.datasets.forEach((dataset, index) => {
                if (dataset.label === targetLabel) {
                    const meta = chart.getDatasetMeta(index);
                    meta.hidden = !meta.hidden;
                }
            });
            
            chart.update();
        }

        // ---------- Helpers para séries / índices ----------
        function sortByAnoMesAsc(arr, getter) {
          return arr.slice().sort((a,b) => getter(a) - getter(b));
        }

        function yyyymmToDateKey(n) {
          const s = n.toString().padStart(6,'0');
          return { y: parseInt(s.slice(0,4)), m: parseInt(s.slice(4,6)) };
        }

        function formatMesAbrev(yyyymm) {
          const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
          const { y, m } = yyyymmToDateKey(yyyymm);
          return `${meses[m-1]}/${y}`;
        }

        // INCC base 100 no 1º mês da série, encadeando variações mensais
        function buildMonthlyInccIndex(inccRows) {
          if (!inccRows || inccRows.length === 0) return { labels: [], index: [] };
          const ordered = sortByAnoMesAsc(inccRows, r => r.ANO_MES || 0);
          const labels = [];
          const index = [];
          let level = 100.0; // base
          ordered.forEach((r, i) => {
            const varMensal = (r.VAR_MENSAL || 0) / 100.0;
            if (i === 0) {
              // primeiro mês fica 100
              labels.push(formatMesAbrev(r.ANO_MES));
              index.push(level);
            } else {
              level = level * (1 + varMensal);
              labels.push(formatMesAbrev(r.ANO_MES));
              index.push(level);
            }
          });
          return { labels, index, monthsOrdered: ordered.map(r => r.ANO_MES) };
        }



        // Valor médio ponderado de venda mensal (residencial, vendidos)
        // e índice base 100 no 1º mês disponível
        function buildMonthlyResidentialPriceIndex(resRows) {
          // agregação mensal: soma AREA_QUANTIDADE_VALOR e AREA_QUANTIDADE apenas para vendidos
          const vendidos = resRows.filter(r =>
            r.OFERTA_VENDA === 'VENDIDOS' || r.OFERTA_VENDA === 'VENDIDOS - LANCADOS E VENDIDOS'
          );
          const byMonth = {};
          vendidos.forEach(r => {
            const p = r.ANO_MES;
            if (!byMonth[p]) byMonth[p] = { val: 0, area: 0 };
            byMonth[p].val += (r.AREA_QUANTIDADE_VALOR || 0);
            byMonth[p].area += (r.AREA_QUANTIDADE || 0);
          });

          const months = Object.keys(byMonth).map(n => parseInt(n,10)).sort((a,b)=>a-b);
          if (months.length === 0) return { labels: [], index: [], monthsOrdered: [] };

          // preço ponderado mensal
          const priceMonthly = months.map(m => {
            const v = byMonth[m];
            return v.area > 0 ? (v.val / v.area) : null;
          });

          // base 100 no 1º mês com valor válido
          let base = null;
          for (let i=0; i<priceMonthly.length; i++) {
            if (priceMonthly[i] !== null && priceMonthly[i] > 0) { base = priceMonthly[i]; break; }
          }
          if (base === null) return { labels: [], index: [], monthsOrdered: [] };

          const index = priceMonthly.map(p => (p && p>0) ? (p / base) * 100.0 : null);
          const labels = months.map(formatMesAbrev);

          return { labels, index, monthsOrdered: months };
        }

        // Valor médio ponderado de oferta mensal (inclui OFERTA, OFERTADOS DISPONIVEIS, OFERTADOS LANCAMENTOS)
        function buildMonthlyResidentialOfferIndex(resRows) {
          const ofertas = resRows.filter(r =>
            r.OFERTA_VENDA === 'OFERTA' ||
            r.OFERTA_VENDA === 'OFERTADOS DISPONIVEIS' ||
            r.OFERTA_VENDA === 'OFERTADOS LANCAMENTOS'
          );

          const byMonth = {};
          ofertas.forEach(r => {
            const p = r.ANO_MES;
            if (!byMonth[p]) byMonth[p] = { val: 0, area: 0 };
            byMonth[p].val += (r.AREA_QUANTIDADE_VALOR || 0);
            byMonth[p].area += (r.AREA_QUANTIDADE || 0);
          });

          const months = Object.keys(byMonth).map(n => parseInt(n,10)).sort((a,b)=>a-b);
          if (months.length === 0) return { labels: [], index: [], monthsOrdered: [] };

          const priceMonthly = months.map(m => {
            const v = byMonth[m];
            return v.area > 0 ? (v.val / v.area) : null;
          });

          let base = null;
          for (let i=0; i<priceMonthly.length; i++) {
            if (priceMonthly[i] !== null && priceMonthly[i] > 0) { base = priceMonthly[i]; break; }
          }
          if (base === null) return { labels: [], index: [], monthsOrdered: [] };

          const index = priceMonthly.map(p => (p && p>0) ? (p / base) * 100.0 : null);
          const labels = months.map(formatMesAbrev);

          return { labels, index, monthsOrdered: months };
        }


        function renderInccPrecoChart(canvasId, inccSeries, priceSeries, offerSeries) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;

            const setIncc = new Set(inccSeries.monthsOrdered);
            const setRes  = new Set(priceSeries.monthsOrdered);
            const setOff  = new Set(offerSeries.monthsOrdered);
            const commonMonths = inccSeries.monthsOrdered.filter(m => setRes.has(m) && setOff.has(m));
            if (commonMonths.length === 0) return;

            const labels   = commonMonths.map(formatMesAbrev);
            const inccData = commonMonths.map(m => inccSeries.index[inccSeries.monthsOrdered.indexOf(m)]);
            const resData  = commonMonths.map(m => priceSeries.index[priceSeries.monthsOrdered.indexOf(m)]);
            const offData  = commonMonths.map(m => offerSeries.index[offerSeries.monthsOrdered.indexOf(m)]);

            if (ctx._chartInstance) ctx._chartInstance.destroy();

            ctx._chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'INCC-M (base=100)',
                            data: inccData,
                            borderColor: '#E74C3C',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            borderWidth: 2,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            tension: 0.1
                        },
                        {
                            label: 'Valor Médio Ponderado de Venda (base=100)',
                            data: resData,
                            borderColor: '#3498DB',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            tension: 0.1
                        },
                        {
                            label: 'Valor Médio Ponderado de Oferta (base=100)',
                            data: offData,
                            borderColor: '#27AE60',
                            backgroundColor: 'rgba(39, 174, 96, 0.1)',
                            borderWidth: 2,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            labels: { usePointStyle: true },
                            onClick: (e, legendItem, legend) => {
                                const index = legendItem.datasetIndex;
                                const chart = legend.chart;
                                const meta = chart.getDatasetMeta(index);
                                meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                                chart.update();

                                // Atualiza o texto de correlação ao clicar
                                const label = legendItem.text || legendItem.dataset.label;
                                const keyMap = {
                                    'IVV': 'ivv',
                                    'Oferta': 'oferta',
                                    'Venda': 'venda',
                                    'Preço Médio': 'precoMedio'
                                };
                                const variableKey = keyMap[label] || 'ivv';
                                const variableLabel = label;

                                const corrEl = document.getElementById('correlationAnalysis');
                                if (corrEl && typeof renderCorrelationNarrative === 'function') {
                                    if (meta.hidden) {
                                        corrEl.innerHTML = `<em>Selecione uma variável de mercado (IVV, Oferta, Venda, VGL, VGV ou Lançamentos) na legenda para ver as correlações com os indicadores econômicos.</em>`;
                                    } else {
                                        renderCorrelationNarrative('correlationAnalysis', variableKey, variableLabel, economicData, secondaryVars);
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Índice (base = 100)',
                                font: { size: 12, weight: 'bold' }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Período',
                                font: { size: 12, weight: 'bold' }
                            }
                        }
                    }
                }
            });
        }

        // Renderizar gráfico de indicadores econômicos com eixo secundário
        function renderEconomicIndicatorsChart(canvasId, primaryData, secondaryData) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            
            console.log('renderEconomicIndicatorsChart: primaryData recebido:', primaryData);
            console.log('renderEconomicIndicatorsChart: secondaryData recebido:', secondaryData);
            
            if (ctx._chartInstance) ctx._chartInstance.destroy();
            
            // *** FUNÇÃO PARA ALINHAR PERÍODOS ***
            function alignSecondaryData(primaryPeriods, secondaryPeriods, secondaryValues) {
                if (!primaryPeriods || !secondaryPeriods || !secondaryValues) {
                    console.log('Dados insuficientes para alinhamento:', { primaryPeriods, secondaryPeriods, secondaryValues });
                    return new Array(primaryPeriods?.length || 0).fill(0);
                }
                
                const alignedData = [];
                primaryPeriods.forEach(primaryPeriod => {
                    const secondaryIndex = secondaryPeriods.indexOf(primaryPeriod);
                    if (secondaryIndex !== -1) {
                        alignedData.push(secondaryValues[secondaryIndex] || 0);
                    } else {
                        alignedData.push(0); // Preenche com 0 quando não há dados para o período
                    }
                });
                
                console.log(`Alinhamento: ${primaryPeriods.length} períodos primários, ${secondaryPeriods.length} períodos secundários, resultado: ${alignedData.length}`);
                return alignedData;
            }
            
            // Alinhar todas as variáveis secundárias com os períodos primários
            const alignedSecondaryData = {
                ivv: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.ivv),
                oferta: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.oferta),
                venda: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.venda),
                vgl: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.vgl),
                vgv: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.vgv),
                lancamentos: alignSecondaryData(primaryData.periods, secondaryData.periods, secondaryData.lancamentos)
            };
            
            console.log('Dados secundários alinhados:', alignedSecondaryData);
            
            // Atualizar variáveis globais com dados alinhados para correlações
            window.secondaryVars = {
                periods: primaryData.periods, // Usar períodos alinhados
                labels: primaryData.labels,   // Usar labels alinhados  
                ivv: alignedSecondaryData.ivv,
                oferta: alignedSecondaryData.oferta,
                venda: alignedSecondaryData.venda,
                vgl: alignedSecondaryData.vgl,
                vgv: alignedSecondaryData.vgv,
                lancamentos: alignedSecondaryData.lancamentos
            };
            
            // Datasets primários (linhas)
            const datasets = [
                {
                    label: 'SELIC (% a.a.)',
                    data: primaryData.selic,
                    borderColor: '#E74C3C',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.1,
                    yAxisID: 'y',
                    order: 1
                },
                {
                    label: 'IPCA 12 meses (%)',
                    data: primaryData.ipca,
                    borderColor: '#3498DB',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.1,
                    yAxisID: 'y',
                    order: 1
                },
                {
                    label: 'Juros Reais (% a.a.)',
                    data: primaryData.jurosReais,
                    borderColor: '#27AE60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.1,
                    yAxisID: 'y',
                    order: 1
                },
                {
                    label: 'INCC-M 12 meses (%)',
                    data: primaryData.incc,
                    borderColor: '#9B59B6',
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.1,
                    yAxisID: 'y',
                    order: 1
                }
            ];
            
            // Datasets secundários (barras) - inicialmente ocultos - USANDO DADOS ALINHADOS
            const secondaryDatasets = {
                ivv: {
                    label: 'IVV - Base 100 (MM 3m)',
                    data: alignedSecondaryData.ivv,
                    backgroundColor: 'rgba(52, 73, 94, 0.3)',
                    borderColor: 'rgba(52, 73, 94, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                },
                oferta: {
                    label: 'OFERTA - Base 100 (MM 3m)',
                    data: alignedSecondaryData.oferta,
                    backgroundColor: 'rgba(230, 126, 34, 0.3)',
                    borderColor: 'rgba(230, 126, 34, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                },
                venda: {
                    label: 'VENDA - Base 100 (MM 3m)',
                    data: alignedSecondaryData.venda,
                    backgroundColor: 'rgba(46, 204, 113, 0.3)',
                    borderColor: 'rgba(46, 204, 113, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                },
                vgl: {
                    label: 'VGL - Base 100 (MM 3m)',
                    data: alignedSecondaryData.vgl,
                    backgroundColor: 'rgba(155, 89, 182, 0.3)',
                    borderColor: 'rgba(155, 89, 182, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                },
                vgv: {
                    label: 'VGV - Base 100 (MM 3m)',
                    data: alignedSecondaryData.vgv,
                    backgroundColor: 'rgba(52, 152, 219, 0.3)',
                    borderColor: 'rgba(52, 152, 219, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                },
                lancamentos: {
                    label: 'Lançamentos - Base 100 (MM 3m)',
                    data: alignedSecondaryData.lancamentos,
                    backgroundColor: 'rgba(231, 76, 60, 0.3)',
                    borderColor: 'rgba(231, 76, 60, 0.6)',
                    borderWidth: 1,
                    type: 'bar',
                    yAxisID: 'y2',
                    order: 2,
                    hidden: true
                }
            };
            
            // Adicionar todos os datasets
            Object.values(secondaryDatasets).forEach(ds => datasets.push(ds));
            console.log('renderEconomicIndicatorsChart: total datasets criados:', datasets.length);
            console.log('renderEconomicIndicatorsChart: datasets:', datasets.map(d => ({ label: d.label, dataLength: d.data?.length })));
            
            ctx._chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: primaryData.labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 10,
                                font: { size: 11 }
                            },
                            onClick: function (e, legendItem, legend) {
                                const chart = legend.chart;
                                const index = legendItem.datasetIndex;
                                const meta = chart.getDatasetMeta(index);

                                // Lógica especial para barras vs linhas
                                const dataset = chart.data.datasets[index];
                                if (dataset.type === 'bar') {
                                    // Para barras: mostrar apenas a clicada, ocultar outras barras
                                    const isCurrentlyVisible = meta.hidden !== true;
                                    if (isCurrentlyVisible) {
                                        // Se já visível, ocultar todas as barras
                                        chart.data.datasets.forEach((ds, i) => {
                                            if (ds.type === 'bar') chart.getDatasetMeta(i).hidden = true;
                                        });
                                    } else {
                                        // Mostrar apenas esta barra, ocultar outras
                                        chart.data.datasets.forEach((ds, i) => {
                                            if (ds.type === 'bar') {
                                                chart.getDatasetMeta(i).hidden = (i !== index);
                                            }
                                        });
                                    }
                                } else {
                                    // Para linhas: toggle normal
                                    meta.hidden = meta.hidden === null ? true : null;
                                }
                                chart.update();
                                
                                const corrEl = document.getElementById('correlationAnalysis');
                                if (!corrEl || typeof renderCorrelationNarrative !== 'function') return;

                                // CORREÇÃO: Extrair nome da variável de forma mais robusta
                                const fullLabel = legendItem.text || dataset.label || "";
                                console.log('🏷️ Label completo:', fullLabel);
                                
                                // Extrair a primeira palavra (nome da variável) antes de qualquer separador
                                let cleanLabel = fullLabel.split(' ')[0].trim().toUpperCase();
                                console.log('🏷️ Label limpo:', cleanLabel);

                                // Mapeamento das variáveis de mercado
                                const keyMap = {
                                    "IVV": "ivv",
                                    "OFERTA": "oferta", 
                                    "VENDA": "venda",
                                    "VGL": "vgl",
                                    "VGV": "vgv",
                                    "LANÇAMENTOS": "lancamentos"
                                };

                                const variableKey = keyMap[cleanLabel] || null;
                                console.log('🔑 Variable key mapeada:', variableKey);

                                // Se não for uma variável de mercado, reseta o texto
                                if (!variableKey) {
                                    console.log('❌ Não é variável de mercado:', cleanLabel);
                                    corrEl.innerHTML = `<em>Selecione uma variável de mercado (IVV, Oferta, Venda, VGL, VGV ou Lançamentos) na legenda para ver as correlações com os indicadores econômicos.</em>`;
                                    return;
                                }

                                // Verificar se a variável está visível (para barras, hidden=false significa visível)
                                const isVisible = (dataset.type === 'bar') ? (meta.hidden === false) : (meta.hidden !== true);
                                console.log('👁️ Variável visível?', isVisible, 'meta.hidden:', meta.hidden);
                                
                                if (!isVisible) {
                                    console.log('👁️ Variável oculta, resetando correlações');
                                    corrEl.innerHTML = `<em>Selecione uma variável de mercado (IVV, Oferta, Venda, VGL, VGV ou Lançamentos) na legenda para ver as correlações com os indicadores econômicos.</em>`;
                                    return;
                                }

                                // Atualiza narrativa dinâmica
                                console.log('🎯 INICIANDO CÁLCULO DE CORRELAÇÃO');
                                console.log('📊 Parâmetros:', { variableKey, cleanLabel });
                                console.log('🌐 Dados globais disponíveis:', {
                                    hasEconomicData: !!window.economicData,
                                    hasSecondaryVars: !!window.secondaryVars
                                });
                                
                                if (window.economicData && window.secondaryVars) {
                                    console.log('✅ Dados globais OK');
                                    console.log('📈 EconomicData keys:', Object.keys(window.economicData));
                                    console.log('📊 SecondaryVars keys:', Object.keys(window.secondaryVars));
                                    console.log('🎯 Variable específica [' + variableKey + ']:', window.secondaryVars[variableKey]?.slice(0, 3));
                                } else {
                                    console.log('❌ Dados globais FALTANDO');
                                }
                                
                                console.log('🚀 Chamando renderCorrelationNarrative...');
                                renderCorrelationNarrative(
                                    'correlationAnalysis',
                                    variableKey,
                                    cleanLabel,
                                    window.economicData,
                                    window.secondaryVars
                                );
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    let label = context.dataset.label || '';
                                    
                                    // Verificar se é variável de mercado (Base 100) ou indicador econômico (%)
                                    const isMarketVariable = label.includes('Base 100');
                                    
                                    if (label) label += ': ';
                                    
                                    if (isMarketVariable) {
                                        // Para variáveis de mercado: mostrar como índice Base 100
                                        label += context.parsed.y.toFixed(1).replace('.', ',');
                                    } else {
                                        // Para indicadores econômicos: mostrar com %
                                        label += context.parsed.y.toFixed(2).replace('.', ',') + '%';
                                    }
                                    
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Indicadores Econômicos (%)',
                                font: { size: 12, weight: 'bold' }
                            },
                            ticks: {
                                callback: function (value) {
                                    return value.toFixed(1).replace('.', ',') + '%';
                                }
                            },
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        y2: {
                            type: 'linear',
                            position: 'right',
                            beginAtZero: true,
                            grace: '5%',
                            title: { display: true, text: 'Variáveis de Mercado - Base 100 (MM 3m)' },
                            grid: { drawOnChartArea: false },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(0);
                                }
                            }
                        },
                        x: { grid: { display: false } }
                    }
                }
            });
           
            // Salvar referência global para controle externo
            window.economicChart = ctx._chartInstance;
            
            // Log final para verificar se window.secondaryVars foi setado corretamente
            console.log('✅ renderEconomicIndicatorsChart finalizado');
            console.log('🎯 window.secondaryVars setado:', window.secondaryVars ? 'SIM' : 'NÃO');
            console.log('🎯 window.economicData setado:', window.economicData ? 'SIM' : 'NÃO');
            if (window.secondaryVars) {
                console.log('📊 Variáveis disponíveis:', Object.keys(window.secondaryVars));
                console.log('📈 IVV (primeiros 5):', window.secondaryVars.ivv?.slice(0, 5));
                console.log('📈 Oferta (primeiros 5):', window.secondaryVars.oferta?.slice(0, 5));
            }
        }

        function displayInsights() {
          // Obter dados de insights do escopo local ou do objeto global "window".
          // Isso evita erros de escopo caso insightsData não esteja definido neste contexto.
          const insightsDataLocal = (typeof insightsData !== 'undefined' ? insightsData : (window.insightsData || {}));
          console.log('insightsData (local/global):', insightsDataLocal);
          
          const container = document.getElementById('tablesContainer');
          if (!container) {
            console.error('displayInsights: Container tablesContainer não encontrado!');
            return;
          }

          // Forçar exibição para debug - removendo verificações muito restritivas
          console.log('displayInsights: Exibindo conteúdo de insights...');
          
          // Verificar se temos pelo menos algum dado
          const hasIPCA = insightsDataLocal && insightsDataLocal.ipca && Array.isArray(insightsDataLocal.ipca) && insightsDataLocal.ipca.length > 0;
          const hasSELIC = insightsDataLocal && insightsDataLocal.selic && Array.isArray(insightsDataLocal.selic) && insightsDataLocal.selic.length > 0;
          const hasJurosReais = insightsDataLocal && insightsDataLocal.jurosReais && Array.isArray(insightsDataLocal.jurosReais) && insightsDataLocal.jurosReais.length > 0;
          const hasINCC = insightsDataLocal && insightsDataLocal.incc && Array.isArray(insightsDataLocal.incc) && insightsDataLocal.incc.length > 0;
          
          console.log('Dados disponíveis:', { hasIPCA, hasSELIC, hasJurosReais, hasINCC });
          
          if (!hasIPCA && !hasSELIC && !hasJurosReais && !hasINCC) {
            container.innerHTML = '<div class="no-data">Dados de Insights não disponíveis. Adicione as abas IPCA, SELIC, JUROS_REAIS ou INCC no arquivo Excel.</div>';
            return;
          }

          // 2) Helpers
          function formatPeriod(anoMes) {
            if (!anoMes) return 'N/D';
            const str = anoMes.toString().padStart(6, '0');
            const ano = str.substring(0, 4);
            const mes = str.substring(4, 6);
            const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
            return meses[parseInt(mes, 10) - 1] + '/' + ano;
          }

          // 3) Últimos registros - versão defensiva
          const lastIPCA = (hasIPCA) ? insightsDataLocal.ipca[insightsDataLocal.ipca.length - 1] : null;
          const lastSELIC = (hasSELIC) ? insightsDataLocal.selic[insightsDataLocal.selic.length - 1] : null;
          const lastJurosReais = (hasJurosReais) ? insightsDataLocal.jurosReais[insightsDataLocal.jurosReais.length - 1] : null;
          const lastINCC = (hasINCC) ? insightsDataLocal.incc[insightsDataLocal.incc.length - 1] : null;

          console.log('Últimos registros:', { lastIPCA, lastSELIC, lastJurosReais, lastINCC });

          // 4) Montagem do HTML (em ordem, sem quebrar template strings)
          let insightsHtml = '<div class="insights-container">';

          // --- Card SELIC
          if (lastSELIC) {
            const selicVarMensal = lastSELIC.VAR_MENSAL || 0;
            const selicVarMensalClass = selicVarMensal >= 0 ? 'positive' : 'negative';
            insightsHtml += `
              <div class="insight-card">
                <h3 class="insight-title">📈 SELIC - Taxa Básica de Juros</h3>
                <p class="insight-description">Taxa de juros básica da economia brasileira.</p>
                <div class="insight-metrics">
                  <div class="metric-box" style="grid-column: span 3;">
                    <span class="metric-label">Taxa Mensal</span>
                    <span class="metric-value ${selicVarMensalClass}">${selicVarMensal.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">${formatPeriod(lastSELIC.ANO_MES)}</span>
                  </div>
                </div>
                <p class="insight-note">Fonte: <a href="https://www.bcb.gov.br/controleinflacao/historicotaxasjuros" target="_blank" style="color:#4A90E2;text-decoration:none;">Banco Central do Brasil</a> - Atualizado em ${formatPeriod(lastSELIC.ANO_MES)}</p>
              </div>`;
          }

          // --- Card IPCA
          if (lastIPCA) {
            const ipcaVarMensal = lastIPCA.VAR_MENSAL || 0;
            const ipcaAcumAno = lastIPCA.ACUM_ANO || 0;
            const ipcaAcum12 = lastIPCA.ACUM_12_MESES || 0;
            const ipcaVarMensalClass = ipcaVarMensal >= 0 ? 'positive' : 'negative';
            insightsHtml += `
              <div class="insight-card">
                <h3 class="insight-title">💰 IPCA - Índice Nacional de Preços ao Consumidor Amplo</h3>
                <p class="insight-description">Principal medida da inflação oficial do Brasil.</p>
                <div class="insight-metrics">
                  <div class="metric-box">
                    <span class="metric-label">Variação Mensal</span>
                    <span class="metric-value ${ipcaVarMensalClass}">${(ipcaVarMensal >= 0 ? '+' : '') + ipcaVarMensal.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">${formatPeriod(lastIPCA.ANO_MES)}</span>
                  </div>
                  <div class="metric-box">
                    <span class="metric-label">Acumulado no Ano</span>
                    <span class="metric-value">${(ipcaAcumAno >= 0 ? '+' : '') + ipcaAcumAno.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">Jan - ${formatPeriod(lastIPCA.ANO_MES)}</span>
                  </div>
                  <div class="metric-box">
                    <span class="metric-label">Acumulado 12 meses</span>
                    <span class="metric-value">${(ipcaAcum12 >= 0 ? '+' : '') + ipcaAcum12.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">Últimos 12 meses</span>
                  </div>
                </div>
                <p class="insight-note">Fonte: <a href="https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html?=&t=downloads" target="_blank" style="color:#4A90E2;text-decoration:none;">Banco Central do Brasil</a> - Atualizado em ${formatPeriod(lastIPCA.ANO_MES)}</p>
              </div>`;
          }

          // --- Card Juros Reais
          if (lastJurosReais) {
            const jr = lastJurosReais.VAR_MENSAL || 0;
            const jrClass = jr >= 0 ? 'positive' : 'negative';
            insightsHtml += `
              <div class="insight-card">
                <h3 class="insight-title">🎯 Juros Reais</h3>
                <p class="insight-description">Taxa de juros descontada da inflação.</p>
                <div class="insight-metrics">
                  <div class="metric-box" style="grid-column: span 3;">
                    <span class="metric-label">Taxa Mensal</span>
                    <span class="metric-value ${jrClass}">${(jr >= 0 ? '+' : '') + jr.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">${formatPeriod(lastJurosReais.ANO_MES)}</span>
                  </div>
                </div>
                <p class="insight-note">Calculado com base nos dados da SELIC e IPCA. Fórmula: (((1+SELIC/100)/(1+IPCA/100))-1)*100</p>
              </div>`;
          }

          // --- Card INCC-M
          if (lastINCC) {
            const inccVarMensal = lastINCC.VAR_MENSAL || 0;
            const inccAcumAno = lastINCC.ACUM_ANO || 0;
            const inccAcum12 = lastINCC.ACUM_12_MESES || 0;
            const inccVarMensalClass = inccVarMensal >= 0 ? 'positive' : 'negative';
            insightsHtml += `
              <div class="insight-card">
                <h3 class="insight-title">🏗️ INCC-M - Índice Nacional de Custo da Construção</h3>
                <p class="insight-description">Índice que mede a evolução dos custos da construção civil no Brasil.</p>
                <div class="insight-metrics">
                  <div class="metric-box">
                    <span class="metric-label">Variação Mensal</span>
                    <span class="metric-value ${inccVarMensalClass}">${(inccVarMensal >= 0 ? '+' : '') + inccVarMensal.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">${formatPeriod(lastINCC.ANO_MES)}</span>
                  </div>
                  <div class="metric-box">
                    <span class="metric-label">Acumulado no Ano</span>
                    <span class="metric-value positive">${(inccAcumAno >= 0 ? '+' : '') + inccAcumAno.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">${new Date().getFullYear()}</span>
                  </div>
                  <div class="metric-box">
                    <span class="metric-label">Acumulado 12 Meses</span>
                    <span class="metric-value positive">${(inccAcum12 >= 0 ? '+' : '') + inccAcum12.toFixed(2).replace('.', ',')}%</span>
                    <span class="metric-period">Últimos 12 meses</span>
                  </div>
                </div>
                <p class="insight-note">Fonte: <a href="https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9358-indice-nacional-de-custo-da-construcao.html" target="_blank" style="color:#4A90E2;text-decoration:none;">IBGE</a> - Atualizado em ${formatPeriod(lastINCC.ANO_MES)}</p>
              </div>`;
          }

          // --- Card: Evolução dos Indicadores Econômicos (gráfico + correlação)
           if (lastSELIC && lastIPCA && lastJurosReais) {
              insightsHtml += `
                <div class="insight-card">
                  <h3 class="insight-title">📊 Evolução dos Indicadores Econômicos vs. Variáveis de Mercado (Base 100)</h3>
                  <p class="insight-description">
                    Análise comparativa entre indicadores econômicos (SELIC, IPCA, Juros Reais, INCC-M) e variáveis de mercado imobiliário normalizadas em Base 100 com média móvel de 3 meses.
                  </p>

                  <div class="chart-wrapper">
                    <div style="height:50vh; max-height:400px;">
                      <canvas id="economicIndicatorsChart"></canvas>
                    </div>
                  </div>

                  <!-- Rodapé explicativo SEMPRE visível -->
                  <div id="economicInterpretation"
                       style="margin-top:15px; padding:12px; background-color:#f8f9fa;
                              border-left:3px solid #4A90E2; border-radius:4px;
                              font-size:13px; color:#555; line-height:1.6;">
                    <strong>Como interpretar:</strong> 
                    <strong>SELIC</strong> (vermelho) é a taxa básica de juros fixada pelo Banco Central; 
                    <strong>IPCA 12 meses</strong> (azul) mostra a inflação acumulada nos últimos 12 meses; 
                    <strong>Juros Reais</strong> (verde) representa a SELIC descontada da inflação (SELIC - IPCA); 
                    <strong>INCC-M</strong> (roxo) mede a variação de custos na construção civil.
                    <br><br>
                    <strong>Análise de correlações:</strong> Selecione uma variável de mercado na legenda para visualizar suas correlações com os indicadores econômicos. 
                    Juros altos tendem a reduzir demanda por imóveis, enquanto inflação baixa e custos controlados favorecem o setor.
                  </div>
                  
                  <!-- Nota metodológica sobre Base 100 e Média Móvel -->
                  <div style="margin-top:10px; padding:10px; background-color:#e8f4fd; border-left:3px solid #2196F3; border-radius:4px; font-size:12px; color:#666;">
                    <strong>📊 Metodologia:</strong> As variáveis de mercado (IVV, Oferta, Venda, VGL, VGV, Lançamentos) são apresentadas em <strong>Base 100</strong> (normalização dos últimos 12 meses = 100) 
                    com <strong>Média Móvel de 3 meses</strong> para suavizar variações sazonais e facilitar a comparação com os indicadores econômicos. 
                    Esta metodologia permite visualizar tendências de longo prazo e correlações mais claras entre as variáveis.
                  </div>

                  <!-- Rodapé DINÂMICO (narrativa de correlação) -->
                  <div id="correlationAnalysis"
                       style="margin-top:15px; padding:12px; background-color:#f8f9fa;
                              border-left:3px solid #A49EE2; border-radius:4px;
                              font-size:13px; color:#555; line-height:1.6;">
                    <em>Selecione uma variável de mercado (IVV, Oferta, Venda, VGL, VGV ou Lançamentos) na legenda para ver as correlações com os indicadores econômicos.</em>
                  </div>
                </div>
              `;
            }

          insightsHtml += '</div>'; // .insights-container
          container.innerHTML = insightsHtml;

          // 5) Renderizações e cálculos
          try {
            // Para Insights, sempre usar dados residenciais para calcular variáveis de mercado
            const currentData = rawData['residencial'] || [];
            
            // Obter filtros de faixa de valor
            const faixaValorFilters = [];
            const faixaCheckboxes = document.querySelectorAll('#faixaValorContent .dropdown-option:not(.select-all) input:checked');
            if (faixaCheckboxes.length > 0) {
                faixaCheckboxes.forEach(cb => faixaValorFilters.push(cb.value));
            }
            
            // Aplicar filtros se houver seleção
            let filteredData = currentData;
            if (faixaValorFilters.length > 0) {
                filteredData = currentData.filter(row => {
                    if (!row.Faixa_Valor) return false;
                    return faixaValorFilters.includes(row.Faixa_Valor);
                });
            }
            
            console.log('Insights: Dados filtrados:', filteredData.length, 'registros');
            console.log('Insights: insightsData disponível:', insightsData);
            
            // Variáveis de mercado e indicadores econômicos (com dados filtrados)
            const secondaryVars = calculateSecondaryVariables(filteredData);
            console.log('Insights: secondaryVars calculadas:', secondaryVars);
            console.log('Insights: períodos secondaryVars:', secondaryVars.periods);
            console.log('Insights: dados IVV:', secondaryVars.ivv);
            console.log('Insights: dados Oferta:', secondaryVars.oferta);
            console.log('Insights: dados Venda:', secondaryVars.venda);
            
            const economicData  = buildEconomicIndicatorsMonthly(
              insightsData.selic,
              insightsData.ipca,
              insightsData.jurosReais,
              insightsData.incc
            );
            console.log('Insights: economicData calculado:', economicData);
            console.log('Insights: períodos economicData:', economicData.periods);

            // Guarda economicData em window para a legenda usar no clique
            // (secondaryVars será setado dentro de renderEconomicIndicatorsChart com dados alinhados)
            window.economicData  = economicData;

            // Renderiza o gráfico dos indicadores econômicos
            renderEconomicIndicatorsChart('economicIndicatorsChart', economicData, secondaryVars);

            // Deixar mensagem inicial - correlações aparecem quando usuário seleciona variável na legenda

          } catch (err) {
            console.error('Erro ao gerar Insights:', err);
            container.innerHTML = `<div class="no-data">Erro ao carregar insights: ${err.message}</div>`;
          }
        }

        // Alterna entre as visualizações (Residencial, Comercial e Insights)
        function toggleMainMenu(view, event) {
            event.preventDefault();
            event.stopPropagation();
            
            // Fechar todos os outros submenus primeiro
            document.querySelectorAll('.submenu-container').forEach(function(container) {
                if (container.id !== 'submenu-' + view) {
                    container.classList.remove('expanded');
                }
            });
            
            // Atualizar ícones de todos os OUTROS menus para colapsado (exceto o atual)
            document.querySelectorAll('.nav-main .nav-item').forEach(function(item) {
                if (item.getAttribute('data-view') !== view) {
                    const icon = item.querySelector('.expand-icon');
                    if (icon) icon.textContent = '▶';
                    item.classList.remove('expanded');
                }
            });
            
            // Toggle do estado expandido para o menu clicado
            expandedMenus[view] = !expandedMenus[view];
            
            // Atualizar ícone de expansão e estado do menu clicado
            const menuItem = event.target.closest('.nav-item');
            const expandIcon = menuItem.querySelector('.expand-icon');
            const submenuContainer = document.getElementById('submenu-' + view);
            
            if (expandedMenus[view]) {
                // Expandir
                menuItem.classList.add('expanded');
                if (expandIcon) expandIcon.textContent = '▼';
                if (submenuContainer) submenuContainer.classList.add('expanded');
                
                // Ativar esta view
                switchView(view, event);
                
                // Popular submenu se necessário
                populateSubmenu(view);
                
            } else {
                // Colapsar
                menuItem.classList.remove('expanded');
                if (expandIcon) expandIcon.textContent = '▶';
                if (submenuContainer) submenuContainer.classList.remove('expanded');
            }
        }
        
        function populateSubmenu(view) {
            const submenuContainer = document.getElementById('submenu-' + view);
            if (!submenuContainer) return;
            
            // Limpar submenu
            submenuContainer.innerHTML = '';
            
            const categories = viewCategories[view] || [];
            
            categories.forEach(function(cat, idx) {
                const li = document.createElement('li');
                li.className = 'nav-item';
                li.setAttribute('data-category', cat);
                
                // Função de clique que garante que apenas esta categoria seja ativa
                li.onclick = function(event) { 
                    console.log('Clique na categoria:', cat);
                    
                    // Scroll to top ao clicar em submenu
                    const mainContainer = document.getElementById('mainContainer');
                    if (mainContainer) {
                        mainContainer.scrollTop = 0;
                    }
                    
                    // Scroll to top da janela principal
                    window.scrollTo(0, 0);
                    
                    // Scroll to top do body
                    document.body.scrollTop = 0;
                    document.documentElement.scrollTop = 0;
                    
                    const tablesContainer = document.getElementById('tablesContainer');
                    if (tablesContainer) {
                        tablesContainer.scrollTop = 0;
                    }
                    
                    const crossTablesContainer = document.getElementById('crossTablesContainer');
                    if (crossTablesContainer) {
                        crossTablesContainer.scrollTop = 0;
                    }
                    
                    // Remover active de todos os itens do submenu
                    submenuContainer.querySelectorAll('.nav-item').forEach(function(item) {
                        item.classList.remove('active');
                    });
                    
                    // Adicionar active apenas ao clicado
                    li.classList.add('active');
                    
                    // Mostrar apenas as tabelas desta categoria
                    showCategory(cat);
                    
                    event.stopPropagation();
                };
                
                li.innerHTML = '<span class="text">' + getFriendlyName(cat) + '</span>';
                
                if (idx === 0) li.classList.add('active');
                submenuContainer.appendChild(li);
            });
            
            // Verificar se já existe uma categoria ativa no submenu atual
            let hasActiveCategory = false;
            let activeCategoryElement = null;
            
            // Primeiro, verificar se currentCategory está definida e é válida para esta view
            if (currentCategory && categories.includes(currentCategory)) {
                hasActiveCategory = true;
                console.log('Categoria ativa já definida:', currentCategory);
                
                // Encontrar e marcar o elemento correto como ativo
                categories.forEach(function(cat, idx) {
                    const items = submenuContainer.querySelectorAll('.nav-item');
                    if (items[idx] && cat === currentCategory) {
                        items[idx].classList.add('active');
                        activeCategoryElement = items[idx];
                    }
                });
                
                // Mostrar a categoria ativa
                showCategory(currentCategory);
            }
            
            // Mostrar primeira categoria por padrão APENAS se não há categoria ativa
            if (!hasActiveCategory && categories.length > 0) {
                console.log('Inicializando com primeira categoria:', categories[0]);
                showCategory(categories[0]);
            }

            // Após preencher o submenu, aplicar as permissões para ocultar itens restritos
            if (typeof applyMenuPermissions === 'function') {
                applyMenuPermissions();
            }
        }
        
        function switchView(view, event) {
          try {
            currentView = view;
            
            // Limpar filtros automaticamente ao trocar de view
            const allCheckboxes = document.querySelectorAll('.dropdown-content input[type="checkbox"]');
            allCheckboxes.forEach(function(cb) {
                cb.checked = false;
            });
            
            const allRadios = document.querySelectorAll('.dropdown-content input[type="radio"]');
            allRadios.forEach(function(radio) {
                radio.checked = false;
            });

            bairroSystem.clear();

            const textElements = {
                faixaValor: document.getElementById('faixaValorText'),
                faixaArea: document.getElementById('faixaAreaText'),
                estagioObra: document.getElementById('estagioObraText'),
                bairro: document.getElementById('bairroText'),
                quartos: document.getElementById('quartosText'),
                periodo: document.getElementById('periodoText')
            };

            Object.entries(textElements).forEach(function(item) {
                const element = item[1];
                if (element) {
                    if (element.id === 'periodoText') {
                        element.textContent = 'Período mais recente';
                    } else {
                        element.textContent = 'Todos';
                    }
                }
            });
            
            // Scroll to top da área principal sempre que trocar de view
            const mainContainer = document.getElementById('mainContainer');
            if (mainContainer) {
                mainContainer.scrollTop = 0;
            }
            
            // Scroll to top da janela principal
            window.scrollTo(0, 0);
            
            // Scroll to top do body
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
            
            // Scroll to top da área de tabelas
            const tablesContainer = document.getElementById('tablesContainer');
            if (tablesContainer) {
                tablesContainer.scrollTop = 0;
            }
            
            // Scroll to top da área de crosstabs
            const crossTablesContainer = document.getElementById('crossTablesContainer');
            if (crossTablesContainer) {
                crossTablesContainer.scrollTop = 0;
            }
            
            // Declarar variáveis no início para evitar ReferenceError
            const faixaValorGroup = document.getElementById('faixaValorGroup');
            const quartosGroup = document.getElementById('quartosGroup');
            
            // Atualiza estado ativo no menu principal apenas se não for um toggle
            if (!event.target.closest('.expand-icon')) {
                document.querySelectorAll('.nav-main li').forEach(function(item) {
                  if (item.getAttribute('data-view') === view) item.classList.add('active');
                  else item.classList.remove('active');
                });
            }
            
            const filtersContainer = document.querySelector('.filters-container');
            const filterActions = document.querySelector('.filter-actions');
            
            // Obter referências dos grupos de filtros no início
            const faixaAreaGroup = document.getElementById('faixaAreaGroup');
            const estagioObraGroup = document.getElementById('estagioObraGroup');
            const bairroGroup = document.getElementById('bairroGroup');
            const periodoGroup = document.getElementById('periodoGroup');
            
            // INSIGHTS: Apenas Faixa de Valor
            if (view === 'insights') {
              console.log('Configurando filtros para INSIGHTS - apenas Faixa de Valor');
              if (filtersContainer) filtersContainer.style.display = 'block';
              if (filterActions) filterActions.style.display = 'flex';
              
              // Configurar filtros para Insights: APENAS Faixa de Valor
              if (faixaValorGroup) {
                faixaValorGroup.style.display = 'block';
                console.log('Insights: Faixa de Valor MOSTRADO');
              }
              if (faixaAreaGroup) {
                faixaAreaGroup.style.display = 'none';
                console.log('Insights: Área OCULTO');
              }
              if (estagioObraGroup) {
                estagioObraGroup.style.display = 'none';
                console.log('Insights: Estágio da Obra OCULTO');
              }
              if (bairroGroup) {
                bairroGroup.style.display = 'none';
                console.log('Insights: Bairro OCULTO');
              }
              if (quartosGroup) {
                quartosGroup.style.display = 'none';
                console.log('Insights: Quartos OCULTO');
              }
              if (periodoGroup) {
                periodoGroup.style.display = 'none';
                console.log('Insights: Período OCULTO');
              }
              
              document.getElementById('crossTablesContainer').style.display = 'none';
              document.getElementById('tablesContainer').style.display = 'block';
              if (typeof displayInsights === 'function') {
                displayInsights();
              }
              return;
            }
            
            // CROSSTABS: Faixa de Valor + Período
            if (view === 'crosstabs') {
              console.log('Configurando filtros para CROSSTABS - Faixa de Valor + Período');
              if (filtersContainer) filtersContainer.style.display = 'block';
              if (filterActions) filterActions.style.display = 'flex';
              
              // Configurar filtros para Crosstabs: Faixa de Valor + Período
              if (faixaValorGroup) {
                faixaValorGroup.style.display = 'block';
                console.log('Crosstabs: Faixa de Valor MOSTRADO');
              }
              if (faixaAreaGroup) {
                faixaAreaGroup.style.display = 'none';
                console.log('Crosstabs: Área OCULTO');
              }
              if (estagioObraGroup) {
                estagioObraGroup.style.display = 'none';
                console.log('Crosstabs: Estágio da Obra OCULTO');
              }
              if (bairroGroup) {
                bairroGroup.style.display = 'none';
                console.log('Crosstabs: Bairro OCULTO');
              }
              if (quartosGroup) {
                quartosGroup.style.display = 'none';
                console.log('Crosstabs: Quartos OCULTO');
              }
              if (periodoGroup) {
                periodoGroup.style.display = 'block';
                console.log('Crosstabs: Período MOSTRADO');
              }
              
              document.getElementById('crossTablesContainer').style.display = 'block';
              document.getElementById('tablesContainer').style.display = 'none';
              
              populateCrossTabsFilters();
              return;
            }
            
            // RESIDENCIAL e COMERCIAL
            if (filtersContainer) filtersContainer.style.display = 'block';
            if (filterActions) filterActions.style.display = 'flex';
            
            if (view === 'residencial') {
              // Filtros: Faixa de Valor, Área Privativa, Estágio da Obra, Região Administrativa, Número de Quartos
              if (faixaValorGroup) faixaValorGroup.style.display = 'block';
              if (faixaAreaGroup) faixaAreaGroup.style.display = 'block';
              if (estagioObraGroup) estagioObraGroup.style.display = 'block';
              if (bairroGroup) bairroGroup.style.display = 'block';
              if (quartosGroup) quartosGroup.style.display = 'block';
              if (periodoGroup) periodoGroup.style.display = 'none';
              
            } else if (view === 'comercial') {
              // Filtros: Área Privativa, Estágio da Obra, Região Administrativa
              if (faixaValorGroup) faixaValorGroup.style.display = 'none';
              if (faixaAreaGroup) faixaAreaGroup.style.display = 'block';
              if (estagioObraGroup) estagioObraGroup.style.display = 'block';
              if (bairroGroup) bairroGroup.style.display = 'block';
              if (quartosGroup) quartosGroup.style.display = 'none';
              if (periodoGroup) periodoGroup.style.display = 'none';
            }
            
            // Mostrar tabelas normais para residencial e comercial
            if (view === 'residencial' || view === 'comercial') {
              document.getElementById('crossTablesContainer').style.display = 'none';
              document.getElementById('tablesContainer').style.display = 'block';
              if (rawData && rawData[currentView]) {
                updateTables(rawData[currentView]);
              }
            }
            
          } catch (err) {
            console.error('Erro ao alternar view:', err);
          }
        }

        function populateFilters() {
            // Não popular filtros para views especiais
            if (currentView === 'insights' || currentView === 'crosstabs') {
                console.log('populateFilters: Ignorando para view especial:', currentView);
                return;
            }
            
            const data = rawData[currentView] || [];
            
            bairroSystem.populateDropdown(data);
            
            // Processar estágios da obra
            const estagiosRaw = data.map(function(row) {
                let estagio = row.ESTAGIO_OBRA;
                if (!estagio || estagio.toString().trim() === '' || estagio.toString().toLowerCase() === 'nan') {
                    return 'Em branco';
                }
                return estagio.toString().trim();
            });
            
            const estagiosUnicos = Array.from(new Set(estagiosRaw));
            
            // Ordem específica para estágios da obra
            const ordemEstagios = ['Planta', 'Fundação', 'Estrutura', 'Acabamento', 'Pronto', 'Em branco'];
            const estagiosOrdenados = ordemEstagios.filter(function(estagio) { 
                return estagiosUnicos.includes(estagio); 
            });
            
            // Adicionar estágios que não estão na ordem predefinida (caso existam)
            const estagiosNaoMapeados = estagiosUnicos.filter(function(estagio) { 
                return !ordemEstagios.includes(estagio); 
            });
            estagiosNaoMapeados.sort();
            const estagios = estagiosOrdenados.concat(estagiosNaoMapeados);
            
            const estagioContent = document.getElementById('estagioObraContent');
            estagioContent.innerHTML = '';
            
            // Adicionar opção "Selecionar Todos"
            const selectAllDiv = document.createElement('div');
            selectAllDiv.className = 'dropdown-option select-all';
            selectAllDiv.innerHTML = '<input type="checkbox" id="estagioSelectAll"><label for="estagioSelectAll">Selecionar Todos</label>';
            estagioContent.appendChild(selectAllDiv);
            
            document.getElementById('estagioSelectAll').onchange = function() {
                selectAllOptions('estagioObra');
            };
            
            // Adicionar cada estágio
            estagios.forEach(function(estagio, index) {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'dropdown-option';
                
                const checkboxId = 'estagio_' + index;
                optionDiv.innerHTML = '<input type="checkbox" id="' + checkboxId + '" value="' + estagio + '"><label for="' + checkboxId + '">' + estagio + '</label>';
                estagioContent.appendChild(optionDiv);
                
                document.getElementById(checkboxId).onchange = function() {
                    updateDropdownText('estagioObra');
                };
            });
            
            if (currentView === 'residencial') {
                const quartosRaw = Array.from(new Set(data.map(function(row) { return row.QTD_QUARTOS; }).filter(function(q) { 
                    return q !== null && q !== undefined && q !== ''; 
                })));
                
                // Processar e ordenar quartos
                const quartosProcessados = quartosRaw.map(function(qtd) {
                    const num = parseInt(qtd);
                    if (qtd === '4+' || num >= 4) {
                        return { value: '4+', label: '4 ou mais', order: 4 };
                    } else {
                        return { value: qtd.toString(), label: qtd + ' quarto' + (qtd > 1 ? 's' : ''), order: num };
                    }
                });
                
                // Remover duplicatas e ordenar
                const quartosUnicos = quartosProcessados.reduce(function(acc, curr) {
                    if (!acc.find(function(item) { return item.value === curr.value; })) {
                        acc.push(curr);
                    }
                    return acc;
                }, []);
                
                quartosUnicos.sort(function(a, b) { return a.order - b.order; });
                
                const quartosContent = document.getElementById('quartosContent');
                quartosContent.innerHTML = '';
                
                // Adicionar opção "Selecionar Todos"
                const selectAllQuartosDiv = document.createElement('div');
                selectAllQuartosDiv.className = 'dropdown-option select-all';
                selectAllQuartosDiv.innerHTML = '<input type="checkbox" id="quartosSelectAll"><label for="quartosSelectAll">Selecionar Todos</label>';
                quartosContent.appendChild(selectAllQuartosDiv);
                
                document.getElementById('quartosSelectAll').onchange = function() {
                    selectAllOptions('quartos');
                };
                
                // Adicionar cada opção de quartos
                quartosUnicos.forEach(function(item, index) {
                    const optionDiv = document.createElement('div');
                    optionDiv.className = 'dropdown-option';
                    
                    const checkboxId = 'quartos_' + index;
                    optionDiv.innerHTML = '<input type="checkbox" id="' + checkboxId + '" value="' + item.value + '"><label for="' + checkboxId + '">' + item.label + '</label>';
                    quartosContent.appendChild(optionDiv);
                    
                    document.getElementById(checkboxId).onchange = function() {
                        updateDropdownText('quartos');
                    };
                });
            }
        }

        function getSelectedFilters() {
            const filters = {};
            
            if (currentView === 'residencial') {
                const faixaCheckboxes = document.querySelectorAll('#faixaValorContent .dropdown-option:not(.select-all) input:checked');
                filters.faixaValor = Array.from(faixaCheckboxes).map(cb => cb.value);
            } else {
                filters.faixaValor = [];
            }

            // Sempre disponível (residencial e comercial)
            const faixaAreaCheckboxes = document.querySelectorAll('#faixaAreaContent .dropdown-option:not(.select-all) input:checked');
            filters.faixaArea = Array.from(faixaAreaCheckboxes).map(cb => cb.value);
            
            const estagioCheckboxes = document.querySelectorAll('#estagioObraContent .dropdown-option:not(.select-all) input:checked');
            filters.estagioObra = Array.from(estagioCheckboxes).map(cb => cb.value);
            
            filters.bairro = bairroSystem.selectedBairros.slice();
            
            if (currentView === 'residencial') {
                const quartosCheckboxes = document.querySelectorAll('#quartosContent .dropdown-option:not(.select-all) input:checked');
                filters.quartos = Array.from(quartosCheckboxes).map(cb => cb.value);
            } else {
                filters.quartos = [];
            }
            
            return filters;
        }

        function filterData(data, filters) {
            let filteredData = data;
            
            // Faixa de Valor → só residencial
            if (currentView === 'residencial' && filters.faixaValor && filters.faixaValor.length > 0) {
                filteredData = filteredData.filter(function(row) {
                    return filters.faixaValor.includes(row.Faixa_Valor);
                });
            }

            // Faixa de Área → disponível em ambas as views
            if (filters.faixaArea && filters.faixaArea.length > 0) {
                filteredData = filteredData.filter(function(row) {
                    return filters.faixaArea.includes(row.Faixa_Area);
                });
            }
            
            // Estágio da Obra
            if (filters.estagioObra && filters.estagioObra.length > 0) {
                filteredData = filteredData.filter(function(row) {
                    let rowEstagio = row.ESTAGIO_OBRA;
                    if (!rowEstagio || rowEstagio.toString().trim() === '' || rowEstagio.toString().toLowerCase() === 'nan') {
                        rowEstagio = 'Em branco';
                    } else {
                        rowEstagio = rowEstagio.toString().trim();
                    }
                    return filters.estagioObra.includes(rowEstagio);
                });
            }
            
            // Bairro
            if (filters.bairro && filters.bairro.length > 0) {
                filteredData = bairroSystem.filterData(filteredData);
            }
            
            // Quartos → só residencial
            if (currentView === 'residencial' && filters.quartos && filters.quartos.length > 0) {
                filteredData = filteredData.filter(function(row) {
                    let rowQuartos = row.QTD_QUARTOS;
                    if (rowQuartos === null || rowQuartos === undefined || rowQuartos === '') {
                        return false;
                    }
                    
                    // Se for "4+" ou >= 4, comparar com seleção "4+"
                    if ((rowQuartos === '4+' || parseInt(rowQuartos) >= 4) && filters.quartos.includes('4+')) {
                        return true;
                    }
                    
                    // Comparação normal para outros valores
                    return filters.quartos.includes(String(rowQuartos));
                });
            }
            
            return filteredData;
        }

        function applyFilters() {
            if (currentView === 'crosstabs') {
                applyCrossTabsFilters();
            } else if (currentView === 'insights') {
                if (typeof displayInsights === 'function') {
                    displayInsights();
                    // Manter categoria ativa após aplicar filtros
                    if (currentCategory) {
                        showCategory(currentCategory);
                    }
                }
            } else {
                // Lógica original
                bairroSystem.updateSelection();
                const filters = getSelectedFilters();
                const originalData = rawData[currentView];
                const filteredData = filterData(originalData, filters);
                updateTables(filteredData);
            }

            // Fechar dropdowns
            document.querySelectorAll('.dropdown-content').forEach(function(dropdown) {
                dropdown.classList.remove('show');
            });
            document.querySelectorAll('.dropdown-button').forEach(function(btn) {
                btn.classList.remove('open');
            });

            const filterContainer = document.getElementById("filters-container");
            if (filterContainer) {
                filterContainer.style.display = "none";
            }
        }

        function clearFilters() {
            console.log('clearFilters: Iniciando limpeza, categoria ativa:', currentCategory);
            
            const allCheckboxes = document.querySelectorAll('.dropdown-content input[type="checkbox"]');
            allCheckboxes.forEach(function(cb) {
                cb.checked = false;
            });
            
            const allRadios = document.querySelectorAll('.dropdown-content input[type="radio"]');
            allRadios.forEach(function(radio) {
                radio.checked = false;
            });

            bairroSystem.clear();

            const textElements = {
                faixaValor: document.getElementById('faixaValorText'),
                faixaArea: document.getElementById('faixaAreaText'),
                estagioObra: document.getElementById('estagioObraText'),
                bairro: document.getElementById('bairroText'),
                quartos: document.getElementById('quartosText'),
                periodo: document.getElementById('periodoText')
            };

            Object.entries(textElements).forEach(function(item) {
                const element = item[1];
                if (element) {
                    if (element.id === 'periodoText') {
                        element.textContent = 'Período mais recente';
                    } else {
                        element.textContent = 'Todos';
                    }
                }
            });

            document.querySelectorAll('.dropdown-content').forEach(function(dropdown) {
                dropdown.classList.remove('show');
            });
            document.querySelectorAll('.dropdown-button').forEach(function(btn) {
                btn.classList.remove('open');
            });

            // Salvar categoria ativa antes de atualizar dados
            const savedCategory = currentCategory;
            console.log('clearFilters: Categoria salva:', savedCategory);

            if (currentView === 'crosstabs') {
                populateCrossTabsFilters();
            } else if (currentView === 'insights') {
                if (typeof displayInsights === 'function') {
                    displayInsights();
                    // Manter categoria ativa após limpar filtros
                    if (savedCategory) {
                        console.log('clearFilters: Restaurando categoria para insights:', savedCategory);
                        showCategory(savedCategory);
                    }
                }
            } else {
                updateTables(rawData[currentView]);
                // Manter categoria ativa após limpar filtros para residencial e comercial
                if (savedCategory) {
                    console.log('clearFilters: Restaurando categoria para', currentView + ':', savedCategory);
                    
                    // Garantir que o elemento visual também seja marcado como ativo
                    const submenuContainer = document.getElementById('submenu-' + currentView);
                    if (submenuContainer) {
                        // Remover todas as classes active primeiro
                        submenuContainer.querySelectorAll('.nav-item').forEach(function(item) {
                            item.classList.remove('active');
                        });
                        
                        // Encontrar e marcar o item correto como ativo
                        submenuContainer.querySelectorAll('.nav-item').forEach(function(item) {
                            if (item.getAttribute('data-category') === savedCategory) {
                                item.classList.add('active');
                                console.log('clearFilters: Elemento visual marcado como ativo:', savedCategory);
                            }
                        });
                    }
                    
                    showCategory(savedCategory);
                }
            }

            const filterContainer = document.getElementById("filters-container");
            if (filterContainer) {
                filterContainer.style.display = "none";
            }
        }

        function calculateIVV(data) {
            const periods = {};
            
            data.forEach(function(row) {
                const period = row.ANO_MES;
                if (!periods[period]) {
                    periods[period] = { vendas: 0, ofertas: 0 };
                }
                
                if (['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS'].includes(row.OFERTA_VENDA)) {
                    periods[period].vendas += row.QUANTIDADE || 0;
                } else if (['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS'].includes(row.OFERTA_VENDA)) {
                    periods[period].ofertas += row.QUANTIDADE || 0;
                }
            });
            
            const ivvResults = {};
            Object.keys(periods).forEach(function(period) {
                const data = periods[period];
                ivvResults[period] = data.ofertas > 0 ? (data.vendas / data.ofertas) * 100 : 0;
            });
            
            return ivvResults;
        }

        function calculateIndicator(data, ofertaTypes) {
            const periods = {};
            
            data.forEach(function(row) {
                if (ofertaTypes.includes(row.OFERTA_VENDA)) {
                    const period = row.ANO_MES;
                    if (!periods[period]) periods[period] = 0;
                    periods[period] += row.QUANTIDADE || 0;
                }
            });
            
            return periods;
        }

        function calculatePeriodAggregations(data, ofertaTypes, isOferta) {
            isOferta = isOferta || false;
            const monthly = calculateIndicator(data, ofertaTypes);
            
            if (Object.keys(monthly).length === 0) {
                return { monthly: {}, quarterly: {}, yearly: {} };
            }
            
            const monthlyEntries = Object.entries(monthly).map(function(item) {
                const period = item[0];
                const value = item[1];
                return {
                    period: parseInt(period),
                    value: value,
                    year: parseInt(String(period).substring(0, 4)),
                    month: parseInt(String(period).substring(4, 6))
                };
            });
            
            const getQuarter = function(month) {
                if (month >= 1 && month <= 3) return 1;
                if (month >= 4 && month <= 6) return 2;
                if (month >= 7 && month <= 9) return 3;
                return 4;
            };
            
            const quarterlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const quarter = getQuarter(entry.month);
                const key = entry.year + '_' + quarter + 'T';
                
                if (!quarterlyGroups[key]) quarterlyGroups[key] = [];
                quarterlyGroups[key].push(entry.value);
            });
            
            const quarterly = {};
            Object.entries(quarterlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                if (isOferta) {
                    quarterly[key] = Math.round(values.reduce(function(sum, val) { return sum + val; }, 0) / values.length);
                } else {
                    quarterly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
                }
            });
            
            const yearlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const key = entry.year;
                if (!yearlyGroups[key]) yearlyGroups[key] = [];
                yearlyGroups[key].push(entry.value);
            });
            
            const yearly = {};
            Object.entries(yearlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                if (isOferta) {
                    yearly[key] = Math.round(values.reduce(function(sum, val) { return sum + val; }, 0) / values.length);
                } else {
                    yearly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
                }
            });
            
            return { monthly: monthly, quarterly: quarterly, yearly: yearly };
        }

        function calculateIVVPeriodAggregations(data) {
            const monthlyIVV = calculateIVV(data);
            
            if (Object.keys(monthlyIVV).length === 0) {
                return { monthly: {}, quarterly: {}, yearly: {} };
            }
            
            const monthlyEntries = Object.entries(monthlyIVV).map(function(item) {
                const period = item[0];
                const value = item[1];
                return {
                    period: parseInt(period),
                    value: value,
                    year: parseInt(String(period).substring(0, 4)),
                    month: parseInt(String(period).substring(4, 6))
                };
            });
            
            const getQuarter = function(month) {
                if (month >= 1 && month <= 3) return 1;
                if (month >= 4 && month <= 6) return 2;
                if (month >= 7 && month <= 9) return 3;
                return 4;
            };
            
            const quarterlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const quarter = getQuarter(entry.month);
                const key = entry.year + '_' + quarter + 'T';
                
                if (!quarterlyGroups[key]) quarterlyGroups[key] = [];
                quarterlyGroups[key].push(entry.value);
            });
            
            const quarterly = {};
            Object.entries(quarterlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                quarterly[key] = values.reduce(function(sum, val) { return sum + val; }, 0) / values.length;
            });
            
            const yearlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const key = entry.year;
                if (!yearlyGroups[key]) yearlyGroups[key] = [];
                yearlyGroups[key].push(entry.value);
            });
            
            const yearly = {};
            Object.entries(yearlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                yearly[key] = values.reduce(function(sum, val) { return sum + val; }, 0) / values.length;
            });
            
            return { monthly: monthlyIVV, quarterly: quarterly, yearly: yearly };
        }

        function calculateAreaPeriodAggregations(data, ofertaTypes, isOferta) {
            isOferta = isOferta || false;
            const monthly = {};
            
            data.forEach(function(row) {
                if (ofertaTypes.includes(row.OFERTA_VENDA)) {
                    const period = row.ANO_MES;
                    if (!monthly[period]) monthly[period] = 0;
                    monthly[period] += row.AREA_QUANTIDADE || 0;
                }
            });
            
            if (Object.keys(monthly).length === 0) {
                return { monthly: {}, quarterly: {}, yearly: {} };
            }
            
            const monthlyEntries = Object.entries(monthly).map(function(item) {
                const period = item[0];
                const value = item[1];
                return {
                    period: parseInt(period),
                    value: value,
                    year: parseInt(String(period).substring(0, 4)),
                    month: parseInt(String(period).substring(4, 6))
                };
            });
            
            const getQuarter = function(month) {
                if (month >= 1 && month <= 3) return 1;
                if (month >= 4 && month <= 6) return 2;
                if (month >= 7 && month <= 9) return 3;
                return 4;
            };
            
            const quarterlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const quarter = getQuarter(entry.month);
                const key = entry.year + '_' + quarter + 'T';
                
                if (!quarterlyGroups[key]) quarterlyGroups[key] = [];
                quarterlyGroups[key].push(entry.value);
            });
            
            const quarterly = {};
            Object.entries(quarterlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                if (isOferta) {
                    quarterly[key] = Math.round(values.reduce(function(sum, val) { return sum + val; }, 0) / values.length);
                } else {
                    quarterly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
                }
            });
            
            const yearlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const key = entry.year;
                if (!yearlyGroups[key]) yearlyGroups[key] = [];
                yearlyGroups[key].push(entry.value);
            });
            
            const yearly = {};
            Object.entries(yearlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                if (isOferta) {
                    yearly[key] = Math.round(values.reduce(function(sum, val) { return sum + val; }, 0) / values.length);
                } else {
                    yearly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
                }
            });
            
            return { monthly: monthly, quarterly: quarterly, yearly: yearly };
        }

        function calculateValorPonderadoPeriodAggregations(data, ofertaTypes) {
            const monthlyData = {};
            
            data.forEach(function(row) {
                if (ofertaTypes.includes(row.OFERTA_VENDA)) {
                    const period = row.ANO_MES;
                    // Verificar se as colunas necessárias existem e têm valores válidos
                    const areaQuantidadeValor = parseFloat(row.AREA_QUANTIDADE_VALOR) || 0;
                    const areaQuantidade = parseFloat(row.AREA_QUANTIDADE) || 0;
                    
                    if (areaQuantidadeValor > 0 && areaQuantidade > 0) {
                        if (!monthlyData[period]) {
                            monthlyData[period] = { totalValor: 0, totalArea: 0 };
                        }
                        monthlyData[period].totalValor += areaQuantidadeValor;
                        monthlyData[period].totalArea += areaQuantidade;
                    }
                }
            });
            
            const monthly = {};
            Object.entries(monthlyData).forEach(function(item) {
                const period = item[0];
                const data = item[1];
                if (data.totalArea > 0) {
                    monthly[period] = data.totalValor / data.totalArea;
                }
            });
            
            if (Object.keys(monthly).length === 0) {
                return { monthly: {}, quarterly: {}, yearly: {} };
            }
            
            const monthlyEntries = Object.entries(monthlyData).map(function(item) {
                const period = item[0];
                const data = item[1];
                return {
                    period: parseInt(period),
                    totalValor: data.totalValor,
                    totalArea: data.totalArea,
                    year: parseInt(String(period).substring(0, 4)),
                    month: parseInt(String(period).substring(4, 6))
                };
            });
            
            const getQuarter = function(month) {
                if (month >= 1 && month <= 3) return 1;
                if (month >= 4 && month <= 6) return 2;
                if (month >= 7 && month <= 9) return 3;
                return 4;
            };
            
            const quarterlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const quarter = getQuarter(entry.month);
                const key = entry.year + '_' + quarter + 'T';
                
                if (!quarterlyGroups[key]) {
                    quarterlyGroups[key] = { totalValor: 0, totalArea: 0 };
                }
                quarterlyGroups[key].totalValor += entry.totalValor;
                quarterlyGroups[key].totalArea += entry.totalArea;
            });
            
            const quarterly = {};
            Object.entries(quarterlyGroups).forEach(function(item) {
                const key = item[0];
                const data = item[1];
                quarterly[key] = data.totalArea > 0 ? data.totalValor / data.totalArea : 0;
            });
            
            const yearlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const key = entry.year;
                if (!yearlyGroups[key]) {
                    yearlyGroups[key] = { totalValor: 0, totalArea: 0 };
                }
                yearlyGroups[key].totalValor += entry.totalValor;
                yearlyGroups[key].totalArea += entry.totalArea;
            });
            
            const yearly = {};
            Object.entries(yearlyGroups).forEach(function(item) {
                const key = item[0];
                const data = item[1];
                yearly[key] = data.totalArea > 0 ? data.totalValor / data.totalArea : 0;
            });
            
            return { monthly: monthly, quarterly: quarterly, yearly: yearly };
        }

        function calculateVGLVGVPeriodAggregations(data, ofertaTypes) {
            const monthly = {};
            
            data.forEach(function(row) {
                if (ofertaTypes.includes(row.OFERTA_VENDA)) {
                    const period = row.ANO_MES;
                    if (!monthly[period]) monthly[period] = 0;
                    monthly[period] += row.AREA_QUANTIDADE_VALOR || 0;
                }
            });
            
            if (Object.keys(monthly).length === 0) {
                return { monthly: {}, quarterly: {}, yearly: {} };
            }
            
            const monthlyEntries = Object.entries(monthly).map(function(item) {
                const period = item[0];
                const value = item[1];
                return {
                    period: parseInt(period),
                    value: value,
                    year: parseInt(String(period).substring(0, 4)),
                    month: parseInt(String(period).substring(4, 6))
                };
            });
            
            const getQuarter = function(month) {
                if (month >= 1 && month <= 3) return 1;
                if (month >= 4 && month <= 6) return 2;
                if (month >= 7 && month <= 9) return 3;
                return 4;
            };
            
            const quarterlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const quarter = getQuarter(entry.month);
                const key = entry.year + '_' + quarter + 'T';
                
                if (!quarterlyGroups[key]) quarterlyGroups[key] = [];
                quarterlyGroups[key].push(entry.value);
            });
            
            const quarterly = {};
            Object.entries(quarterlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                quarterly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
            });
            
            const yearlyGroups = {};
            monthlyEntries.forEach(function(entry) {
                const key = entry.year;
                if (!yearlyGroups[key]) yearlyGroups[key] = [];
                yearlyGroups[key].push(entry.value);
            });
            
            const yearly = {};
            Object.entries(yearlyGroups).forEach(function(item) {
                const key = item[0];
                const values = item[1];
                yearly[key] = values.reduce(function(sum, val) { return sum + val; }, 0);
            });
            
            return { monthly: monthly, quarterly: quarterly, yearly: yearly };
        }

        function createTable(title, data, isPercentage, projectsData, enterpriseData) {
            enterpriseData = enterpriseData || null;
            isPercentage = isPercentage || false;
            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const currentInfo = getCurrentPeriodInfo();
            const yearlyData = {};
            Object.keys(data).forEach(function(period) {
                const year = String(period).substring(0, 4);
                if (!yearlyData[year]) yearlyData[year] = {};
                yearlyData[year][period] = data[period];
            });

            const years = Object.keys(yearlyData).sort();
            
            // Calcular maior e menor valor por ano (para as setas)
            const yearStats = {};
            years.forEach(function(year) {
                const values = Object.values(yearlyData[year]).filter(v => v !== undefined && v !== null && !isNaN(v));
                if (values.length > 0) {
                    yearStats[year] = {
                        max: Math.max(...values),
                        min: Math.min(...values)
                    };
                }
            });
            
            // Calcular maior e menor valor de TODA a série histórica (para as barras)
            const allValues = [];
            Object.keys(data).forEach(function(period) {
                const value = data[period];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min(...allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max(...allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }
            
            let tableId = 'table_' + title.replace(/\s+/g, '_');
            let tableHtml = `
                <div class="table-card">
                    <div class="table-header">
                        <div class="table-title">${title}</div>
                        <button class="filter-btn apply-btn" onclick="exportAllTablesToPDF()">📄 PDF</button>
                    </div>
                    <table id="${tableId}" class="data-table quarterly-table">
                        <thead><tr><th></th>`;
                            
            // Cabeçalho
            years.forEach(function(year) {
                tableHtml += '<th>' + year + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';

            const months = [
                {num: '01', name: 'Jan'}, {num: '02', name: 'Fev'}, {num: '03', name: 'Mar'},
                {num: '04', name: 'Abr'}, {num: '05', name: 'Mai'}, {num: '06', name: 'Jun'},
                {num: '07', name: 'Jul'}, {num: '08', name: 'Ago'}, {num: '09', name: 'Set'},
                {num: '10', name: 'Out'}, {num: '11', name: 'Nov'}, {num: '12', name: 'Dez'}
            ];

            months.forEach(function(month) {
                tableHtml += '<tr><td>' + month.name + '</td>';
                
                years.forEach(function(year) {
                    const period = parseInt(year + month.num);
                    const value = yearlyData[year][period];
                    const isIncompleteMonthCell = isIncompleteMonthPeriod(period, currentInfo);
                    let displayValue = '';
                    
                    if (value !== undefined && value !== null && !isNaN(value) && value >= 0) {
                        if (isPercentage) {
                            displayValue = value.toFixed(1).replace('.', ',') + '%';
                        } else {
                            displayValue = Math.round(value).toLocaleString('pt-BR');
                        // Adicionar empreendimentos [N] quando for tabela de lançamentos
                            if (title.includes('Lançamentos') && (enterpriseData || projectsData)) {
                                const countsToUse = enterpriseData || projectsData;
                                const empreendimentos = countsToUse[period] || 0;
                                displayValue += ' [' + empreendimentos + ']';
                            }
                        }
                        // Adicionar indicadores de máximo e mínimo (por ano)
                        let indicator = '';
                        if (yearStats[year]) {
                            if (value === yearStats[year].max) {
                                indicator = ' <span style="color: #555;">▲</span>';
                            } else if (value === yearStats[year].min) {
                                indicator = ' <span style="color: #555;">▼</span>';
                            }
                        }
                        
                        if (isIncompleteMonthCell) {
                            displayValue += ' *';
                        }
                        
                        // Calcular largura da barra baseada na série completa
                        const barWidth = getBarWidth(value);
                        
                        tableHtml += '<td><div style="position: relative; padding: 4px 8px; border-radius: 4px;">' +
                            '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth + '%; ' +
                            'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ' +
                            'border-radius: 4px; z-index: 0;"></div>' +
                            '<div style="position: relative; z-index: 1;">' + displayValue + indicator + '</div>' +
                            '</div></td>';
                            
                    } else if (value === 0) {
                        if (isPercentage) {
                            displayValue = '0,0%';
                        } else {
                            displayValue = '0';
                        }
                        if (isIncompleteMonthCell) {
                            displayValue += ' *';
                        }
                        
                        const barWidth = getBarWidth(0);
                        tableHtml += '<td><div style="position: relative; padding: 4px 8px; border-radius: 4px;">' +
                            '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth + '%; ' +
                            'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ' +
                            'border-radius: 4px; z-index: 0;"></div>' +
                            '<div style="position: relative; z-index: 1;">' + displayValue + '</div>' +
                            '</div></td>';
                    } else {
                        tableHtml += '<td></td>';
                    }
                });
                
                tableHtml += '</tr>';
            });

            // Fecha tabela
            tableHtml += '</tbody></table>';

            // Adicionar variações
            const availablePeriods = Object.keys(data).map(p => parseInt(p)).sort();
            if (availablePeriods.length >= 2) {
                const latestPeriod = Math.max(...availablePeriods);
                const latestValue = data[latestPeriod];
                
                if (latestValue !== undefined && latestValue !== null) {
                    let variationsHtml = '<div class="variation-info">';
                    
                    const latestPeriodStr = latestPeriod.toString().padStart(6, '0');
                    const latestYear = parseInt(latestPeriodStr.substring(0, 4));
                    const latestMonth = parseInt(latestPeriodStr.substring(4, 6));
                    
                    let prevMonthPeriod = null;
                    if (latestMonth > 1) {
                        const prevMonth = (latestMonth - 1).toString().padStart(2, '0');
                        prevMonthPeriod = parseInt(latestYear.toString() + prevMonth);
                    } else {
                        prevMonthPeriod = parseInt((latestYear - 1).toString() + '12');
                    }
                    
                    const prevMonthValue = data[prevMonthPeriod];
                    if (prevMonthValue !== undefined && prevMonthValue !== null && prevMonthValue !== 0) {
                        const variation1 = ((latestValue - prevMonthValue) / prevMonthValue) * 100;
                        const colorClass1 = variation1 >= 0 ? 'positive' : 'negative';
                        
                        const latestMonthName = months[latestMonth - 1].name;
                        const prevMonthName = latestMonth > 1 ? months[latestMonth - 2].name : 'dez';
                        const prevYear = latestMonth > 1 ? latestYear : latestYear - 1;
                        
                        variationsHtml += latestMonthName + '/' + latestYear + ' - ' + prevMonthName + '/' + prevYear + ': ' +
                            '<span class="' + colorClass1 + '">' + variation1.toFixed(1).replace('.', ',') + '%</span>';
                    }
                    
                    const prevYearSameMonth = parseInt((latestYear - 1).toString() + latestMonth.toString().padStart(2, '0'));
                    const prevYearValue = data[prevYearSameMonth];
                    
                    if (prevYearValue !== undefined && prevYearValue !== null && prevYearValue !== 0) {
                        if (variationsHtml.includes('span>')) {
                            variationsHtml += ' | ';
                        }
                        
                        const variation2 = ((latestValue - prevYearValue) / prevYearValue) * 100;
                        const colorClass2 = variation2 >= 0 ? 'positive' : 'negative';
                        
                        const latestMonthName = months[latestMonth - 1].name;
                        
                        variationsHtml += latestMonthName + '/' + latestYear + ' - ' + latestMonthName + '/' + (latestYear - 1) + ': ' +
                            '<span class="' + colorClass2 + '">' + variation2.toFixed(1).replace('.', ',') + '%</span>';
                    }
                    
                    variationsHtml += '</div>';
                    tableHtml += variationsHtml;
                }
            }
                    
            tableHtml += '</div>';
            return tableHtml;
        }

        function createQuarterlyTable(title, data, projectsData, enterpriseData) {
            enterpriseData = enterpriseData || null;
            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const currentInfo = getCurrentPeriodInfo();
            const yearlyData = {};
            Object.entries(data).forEach(function(item) {
                const period = item[0];
                const value = item[1];
                const parts = period.split('_');
                const year = parts[0];
                const quarter = parts[1];
                if (!yearlyData[year]) yearlyData[year] = {};
                yearlyData[year][quarter] = value;
            });

            const years = Object.keys(yearlyData).sort();
            const quarters = ['1T', '2T', '3T', '4T'];

            // Calcular maior e menor valor por ano (para as setas)
            const yearStats = {};
            years.forEach(function(year) {
                const values = Object.values(yearlyData[year]).filter(function(v) {
                    return v !== undefined && v !== null && !isNaN(v);
                });
                if (values.length > 0) {
                    yearStats[year] = {
                        max: Math.max.apply(Math, values),
                        min: Math.min.apply(Math, values)
                    };
                }
            });

            // Calcular maior e menor valor de TODA a série histórica (para as barras)
            const allValues = [];
            Object.keys(data).forEach(function(key) {
                const value = data[key];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min.apply(Math, allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max.apply(Math, allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }

            const series = [];
            years.forEach(function(year) {
                quarters.forEach(function(quarter) {
                    const value = yearlyData[year] && yearlyData[year][quarter];
                    if (value !== undefined && value !== null) {
                        series.push({ year: year, quarter: quarter, value: value });
                    }
                });
            });

            let prevValue = null;
            series.forEach(function(point, idx) {
                if (idx === 0) {
                    point.extraClass = 'positive';
                } else {
                    if (point.value > prevValue) point.extraClass = 'positive';
                    else if (point.value < prevValue) point.extraClass = 'negative';
                    else point.extraClass = 'neutral';
                }
                prevValue = point.value;
            });

            let tableId = 'table_' + title.replace(/\s+/g, '_');

            let tableHtml = '<div class="table-card">';
            tableHtml += '<div class="table-header"><div class="table-title">' + title + '</div></div>';
            tableHtml += '<table id="' + tableId + '" class="data-table quarterly-table"><thead><tr><th></th>';

            years.forEach(function(year) {
                let hasIncompleteQuarter = false;
                if (parseInt(year) === currentInfo.maxYear) {
                    const currentQuarterKey = year + '_' + currentInfo.maxQuarter + 'T';
                    hasIncompleteQuarter = isIncompleteQuarter(currentQuarterKey, currentInfo);
                }
                tableHtml += '<th>' + year + (hasIncompleteQuarter ? ' *' : '') + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';

            quarters.forEach(function(quarter) {
                let isQuarterIncomplete = false;
                years.forEach(function(year) {
                    const quarterKey = year + '_' + quarter;
                    if (isIncompleteQuarter(quarterKey, currentInfo)) {
                        isQuarterIncomplete = true;
                    }
                });
                
                const quarterLabel = quarter + (isQuarterIncomplete ? ' *' : '');
                tableHtml += '<tr><td>' + quarterLabel + '</td>';
                
                years.forEach(function(year) {
                    const value = yearlyData[year] && yearlyData[year][quarter];
                    let displayValue = '';
                    let extraClass = '';

                    if (value !== undefined && value !== null) {
                        if (title.indexOf('IVV') > -1) {
                            displayValue = value.toFixed(1).replace('.', ',') + '%';
                        } else {
                            displayValue = Math.round(value).toLocaleString('pt-BR');
                        // Adicionar empreendimentos [N]
                            if (title.includes('Lançamentos') && (enterpriseData || projectsData)) {
                                const countsToUse = enterpriseData || projectsData;
                                const empreendimentos = countsToUse[year + '_' + quarter] || 0;
                                displayValue += ' [' + empreendimentos + ']';
                            }
                        }
                        
                        // Adicionar indicadores de máximo e mínimo (por ano)
                        let indicator = '';
                        if (yearStats[year]) {
                            if (value === yearStats[year].max) {
                                indicator = ' <span style="color: #555;">▲</span>';
                            } else if (value === yearStats[year].min) {
                                indicator = ' <span style="color: #555;">▼</span>';
                            }
                        }

                        const point = series.find(function(p) { return p.year === year && p.quarter === quarter; });
                        extraClass = point ? point.extraClass : '';
                        
                        // Calcular largura da barra baseada na série completa
                        const barWidth = getBarWidth(value);
                        
                        tableHtml += '<td class="' + extraClass + '">';
                        tableHtml += '<div style="position: relative; padding: 4px 8px; border-radius: 4px;">';
                        tableHtml += '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth.toFixed(2) + '%; ';
                        tableHtml += 'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ';
                        tableHtml += 'border-radius: 4px; z-index: 0;"></div>';
                        tableHtml += '<div style="position: relative; z-index: 1;">' + displayValue + indicator + '</div>';
                        tableHtml += '</div>';
                        tableHtml += '</td>';
                    } else {
                        tableHtml += '<td></td>';
                    }
                });

                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';

            if (series.length > 1) {
                const lastPoint = series[series.length - 1];
                const prevPoint = series[series.length - 2];

                let prevYearPoint = null;
                for (let i = series.length - 1; i >= 0; i--) {
                    if (series[i].quarter === lastPoint.quarter && series[i].year === (parseInt(lastPoint.year) - 1).toString()) {
                        prevYearPoint = series[i];
                        break;
                    }
                }

                function formatVariation(label, diff) {
                    let cssClass = 'neutral';
                    if (diff > 0) cssClass = 'positive';
                    else if (diff < 0) cssClass = 'negative';
                    return label + ': <span class="' + cssClass + '">' + diff.toFixed(1).replace('.', ',') + '%</span>';
                }

                let variationPrev = '';
                let variationYear = '';

                if (prevPoint) {
                    const diff = ((lastPoint.value / prevPoint.value) - 1) * 100;
                    variationPrev = formatVariation(lastPoint.quarter + '/' + lastPoint.year + ' - ' + prevPoint.quarter + '/' + prevPoint.year, diff);
                }

                if (prevYearPoint) {
                    const diffYear = ((lastPoint.value / prevYearPoint.value) - 1) * 100;
                    variationYear = formatVariation(lastPoint.quarter + '/' + lastPoint.year + ' - ' + prevYearPoint.quarter + '/' + prevYearPoint.year, diffYear);
                }

                if (variationPrev || variationYear) {
                    tableHtml += '<div class="variation-info">';
                    const parts = [];
                    if (variationPrev) parts.push(variationPrev);
                    if (variationYear) parts.push(variationYear);
                    tableHtml += parts.join(' | ');
                    tableHtml += '</div>';
                }
            }

            const hasIncompleteData = (function() {
                const currentQuarterKey = currentInfo.maxYear + '_' + currentInfo.maxQuarter + 'T';
                return isIncompleteQuarter(currentQuarterKey, currentInfo);
            })();
            
            if (hasIncompleteData) {
                tableHtml += '<div style="font-size: 12px; color: #1976D2; margin-top: 10px; padding: 8px; background-color: #E3F2FD; border-radius: 4px;">';
                const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                const lastAvailableMonth = currentInfo.maxMonth;  
                const lastAvailableYear = currentInfo.maxYear;
                const monthLabel = lastAvailableMonth ? monthNames[lastAvailableMonth - 1] : '';
                tableHtml += '* Trimestre incompleto (dados até ' + monthLabel + '/' + lastAvailableYear + ')';
                tableHtml += '</div>';
            }
            
            tableHtml += '</div>';
            return tableHtml;
        }

        function createYearlyTable(title, data, projectsData, enterpriseData) {
            enterpriseData = enterpriseData || null;
            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const currentInfo = getCurrentPeriodInfo();
            const years = Object.keys(data).sort();

            // Calcular maior e menor valor da série (para as setas)
            const allValues = [];
            Object.keys(data).forEach(function(year) {
                const value = data[year];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min.apply(Math, allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max.apply(Math, allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }

            let tableId = 'table_' + title.replace(/\s+/g, '_');

            let tableHtml = '<div class="table-card">';
            tableHtml += '<div class="table-header">';
            tableHtml += '<div class="table-title">' + title + '</div>';
            tableHtml += '</div>';
            tableHtml += '<table id="' + tableId + '" class="data-table yearly-table">';
            tableHtml += '<thead><tr><th>Ano</th><th>Valor</th>';

            if (years.length > 1) {
                tableHtml += '<th>Var %</th>';
            }

            tableHtml += '</tr></thead><tbody>';

            years.forEach(function(year, index) {
                const value = data[year];
                const isIncompleteYearData = isIncompleteYear(year, currentInfo);
                let displayValue = '';
                let variationText = '';
                let valueClass = 'neutral';

                if (value !== undefined && value !== null) {
                    if (title.indexOf('IVV') > -1) {
                        displayValue = value.toFixed(1).replace('.', ',') + '%';
                    } else {
                        displayValue = Math.round(value).toLocaleString('pt-BR');
                    // Adicionar empreendimentos [N]
                        if (title.includes('Lançamentos') && (enterpriseData || projectsData)) {
                            const countsToUse = enterpriseData || projectsData;
                            const empreendimentos = countsToUse[year] || 0;
                            displayValue += ' [' + empreendimentos + ']';
                        }

                    }
                    // Adicionar setas para maior e menor valor
                    let indicator = '';
                    if (value === seriesMax) {
                        indicator = ' <span style="color: #555;">▲</span>';
                    } else if (value === seriesMin) {
                        indicator = ' <span style="color: #555;">▼</span>';
                    }
                    displayValue += indicator;

                    if (index === 0) {
                        valueClass = 'positive';
                    } else {
                        const prevYear = years[index - 1];
                        const prevValue = data[prevYear];
                        if (prevValue !== undefined && prevValue !== null && prevValue !== 0) {
                            if (value > prevValue) valueClass = 'positive';
                            else if (value < prevValue) valueClass = 'negative';
                        }
                    }
                }

                if (index > 0 && years.length > 1) {
                    const prevYear = years[index - 1];
                    const prevValue = data[prevYear];
                    if (prevValue !== undefined && prevValue !== null && !isNaN(prevValue) && prevValue !== 0 &&
                        value !== undefined && value !== null && !isNaN(value)) {
                        const variation = ((value - prevValue) / prevValue) * 100;
                        const sign = variation >= 0 ? '+' : '';
                        variationText = sign + variation.toFixed(1).replace('.', ',') + '%';
                    } else {
                        variationText = '-';
                    }
                } else if (years.length > 1) {
                    variationText = '-';
                }

                const yearLabel = isIncompleteYearData ? year + ' *' : year;

                tableHtml += '<tr><td>' + yearLabel + '</td>';
                
                // Célula com valor e barra
                const barWidth = getBarWidth(value);
                tableHtml += '<td class="' + valueClass + '">';
                tableHtml += '<div style="position: relative; padding: 4px 8px; border-radius: 4px;">';
                tableHtml += '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth.toFixed(2) + '%; ';
                tableHtml += 'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ';
                tableHtml += 'border-radius: 4px; z-index: 0;"></div>';
                tableHtml += '<div style="position: relative; z-index: 1;">' + displayValue + '</div>';
                tableHtml += '</div>';
                tableHtml += '</td>';

                // Coluna de variação (SEM setas)
                if (years.length > 1) {
                    if (variationText !== '-') {
                        const cleaned = variationText.replace('%', '').replace('+', '').replace(',', '.').trim();
                        const variation = parseFloat(cleaned);
                        let cssClass = 'neutral';
                        if (!isNaN(variation)) {
                            if (variation > 0) cssClass = 'positive';
                            else if (variation < 0) cssClass = 'negative';
                        }
                        tableHtml += '<td class="' + cssClass + '">' + variationText + '</td>';
                    } else {
                        tableHtml += '<td>' + variationText + '</td>';
                    }
                }

                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';

            if (years.length > 1) {
                const lastYear = years[years.length - 1];
                const prevYear = years[years.length - 2];
                const firstYear = years[0];

                const lastValue = data[lastYear];
                const prevValue = data[prevYear];
                const firstValue = data[firstYear];

                function formatVariation(label, diff) {
                    let cssClass = 'neutral';
                    if (diff > 0) cssClass = 'positive';
                    else if (diff < 0) cssClass = 'negative';
                    return label + ': <span class="' + cssClass + '">' + diff.toFixed(1).replace('.', ',') + '%</span>';
                }

                let variationPrev = '';
                let variationFirst = '';

                if (lastValue !== undefined && prevValue !== undefined && prevValue !== 0) {
                    const diff = ((lastValue / prevValue) - 1) * 100;
                    variationPrev = formatVariation(lastYear + ' - ' + prevYear, diff);
                }

                if (lastValue !== undefined && firstValue !== undefined && firstValue !== 0) {
                    const diff = ((lastValue / firstValue) - 1) * 100;
                    variationFirst = formatVariation(lastYear + ' - ' + firstYear, diff);
                }

                if (variationPrev || variationFirst) {
                    tableHtml += '<div class="variation-info">';
                    const parts = [];
                    if (variationPrev) parts.push(variationPrev);
                    if (variationFirst) parts.push(variationFirst);
                    tableHtml += parts.join(' | ');
                    tableHtml += '</div>';
                }
            }

            const hasIncompleteData = years.some(function(year) { return isIncompleteYear(year, currentInfo); });
            if (hasIncompleteData) {
                const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                const lastAvailableMonth = currentInfo.maxMonth;  
                const lastAvailableYear = currentInfo.maxYear;
                const monthLabel = lastAvailableMonth ? monthNames[lastAvailableMonth - 1] : '';

                tableHtml += '<div style="font-size: 12px; color: #1976D2; margin-top: 10px; padding: 8px; background-color: #E3F2FD; border-radius: 4px;">';
                tableHtml += '* Ano incompleto (dados até ' + monthLabel + '/' + lastAvailableYear + ')';
                tableHtml += '</div>';
            }
                    
            tableHtml += '</div>';
            return tableHtml;
        }

        function createTableMoney(title, data, isValue) {
            isValue = isValue || false;

            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const yearlyData = {};
            Object.keys(data).forEach(function(period) {
                const year = String(period).substring(0, 4);
                if (!yearlyData[year]) yearlyData[year] = {};
                yearlyData[year][period] = data[period];
            });

            const years = Object.keys(yearlyData).sort((a,b)=>parseInt(a)-parseInt(b));

            // Calcular maior e menor valor por ano (para as setas)
            const yearStats = {};
            years.forEach(function(year) {
                const values = Object.values(yearlyData[year]).filter(v => v !== undefined && v !== null && !isNaN(v));
                if (values.length > 0) {
                    yearStats[year] = {
                        max: Math.max(...values),
                        min: Math.min(...values)
                    };
                }
            });

            // Calcular maior e menor valor de TODA a série histórica (para as barras)
            const allValues = [];
            Object.keys(data).forEach(function(period) {
                const value = data[period];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min(...allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max(...allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }

            const months = [
                {num: '01', name: 'Jan'}, {num: '02', name: 'Fev'}, {num: '03', name: 'Mar'},
                {num: '04', name: 'Abr'}, {num: '05', name: 'Mai'}, {num: '06', name: 'Jun'},
                {num: '07', name: 'Jul'}, {num: '08', name: 'Ago'}, {num: '09', name: 'Set'},
                {num: '10', name: 'Out'}, {num: '11', name: 'Nov'}, {num: '12', name: 'Dez'}
            ];

            const series = [];
            years.forEach(function(year) {
                months.forEach(function(m) {
                    const period = parseInt(year + m.num, 10);
                    const value = yearlyData[year] ? yearlyData[year][period] : undefined;
                    if (value !== undefined && value !== null) {
                        series.push({ year, month: m.num, value, period });
                    }
                });
            });

            let prevValue = null;
            series.forEach((p, i) => {
                if (i === 0) {
                    p.extraClass = 'positive';
                } else {
                    if (p.value > prevValue) p.extraClass = 'positive';
                    else if (p.value < prevValue) p.extraClass = 'negative';
                    else p.extraClass = 'neutral';
                }
                prevValue = p.value;
            });

            let tableId = 'table_' + title.replace(/\s+/g, '_');

            let tableHtml = `
                <div class="table-card">
                    <div class="table-header">
                        <div class="table-title">${title}</div>
                        <button class="filter-btn apply-btn" onclick="exportAllTablesToPDF()">📄 PDF</button>
                    </div>
                    <table id="${tableId}" class="data-table monthly-money-table">
                        <thead><tr><th></th>`;

            years.forEach(function(year) {
                tableHtml += '<th>' + year + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';

            months.forEach(function(m) {
                tableHtml += '<tr><td>' + m.name + '</td>';

                years.forEach(function(year) {
                    const period = parseInt(year + m.num, 10);
                    const value = yearlyData[year] ? yearlyData[year][period] : undefined;

                    let displayValue = '';
                    let extraClass = '';

                    if (value !== undefined && value !== null && !isNaN(value)) {
                        if (isValue) {
                            displayValue = Number(value).toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        } else {
                            const valueInMillions = Number(value) / 1_000_000;
                            displayValue = valueInMillions.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }

                        // Adicionar indicadores de máximo e mínimo (por ano)
                        let indicator = '';
                        if (yearStats[year]) {
                            if (value === yearStats[year].max) {
                                indicator = ' <span style="color: #555;">▲</span>';
                            } else if (value === yearStats[year].min) {
                                indicator = ' <span style="color: #555;">▼</span>';
                            }
                        }

                        const point = series.find(p => p.year === year && p.month === m.num);
                        extraClass = point ? point.extraClass : '';
                        
                        // Calcular largura da barra baseada na série completa
                        const barWidth = getBarWidth(value);
                        
                        tableHtml += '<td class="' + extraClass + '"><div style="position: relative; padding: 4px 8px; border-radius: 4px;">' +
                            '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth + '%; ' +
                            'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ' +
                            'border-radius: 4px; z-index: 0;"></div>' +
                            '<div style="position: relative; z-index: 1;">' + displayValue + indicator + '</div>' +
                            '</div></td>';
                            
                    } else if (value === 0) {
                        displayValue = '0,00';
                        extraClass = 'neutral';
                        
                        const barWidth = getBarWidth(0);
                        tableHtml += '<td class="' + extraClass + '"><div style="position: relative; padding: 4px 8px; border-radius: 4px;">' +
                            '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth + '%; ' +
                            'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ' +
                            'border-radius: 4px; z-index: 0;"></div>' +
                            '<div style="position: relative; z-index: 1;">' + displayValue + '</div>' +
                            '</div></td>';
                    } else {
                        tableHtml += '<td></td>';
                    }
                });

                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';

            // Rodapé (variações) - mantém o código existente
            if (series.length > 0) {
                const lastPoint = series[series.length - 1];
                const prevPoint = series.length > 1 ? series[series.length - 2] : null;

                let prevYearSameMonth = null;
                for (let i = series.length - 1; i >= 0; i--) {
                    if (series[i].month === lastPoint.month &&
                        parseInt(series[i].year, 10) === parseInt(lastPoint.year, 10) - 1) {
                        prevYearSameMonth = series[i];
                        break;
                    }
                }

                const pct = (a, b) => (b === 0 || b == null) ? null : ((a / b) - 1) * 100;
                const label = (p) => {
                    const m = months.find(mm => mm.num === p.month).name;
                    return m + '/' + p.year;
                };
                const spanPct = (diff) => {
                    if (diff === null) return '<span class="neutral">-</span>';
                    const cls = diff > 0 ? 'positive' : diff < 0 ? 'negative' : 'neutral';
                    const sign = diff > 0 ? '+' : '';
                    return `<span class="${cls}">${sign}${diff.toFixed(1).replace('.', ',')}%</span>`;
                };

                const parts = [];
                if (prevPoint) {
                    const d1 = pct(lastPoint.value, prevPoint.value);
                    parts.push(`${label(lastPoint)} - ${label(prevPoint)}: ${spanPct(d1)}`);
                }
                if (prevYearSameMonth) {
                    const d2 = pct(lastPoint.value, prevYearSameMonth.value);
                    parts.push(`${label(lastPoint)} - ${label(prevYearSameMonth)}: ${spanPct(d2)}`);
                }

                if (parts.length) {
                    tableHtml += '<div class="variation-info">' + parts.join(' | ') + '</div>';
                }
            }

            tableHtml += '</div>';
            return tableHtml;
        }

        function createQuarterlyTableMoney(title, data, isValue) {
            isValue = isValue || false;
            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const currentInfo = getCurrentPeriodInfo();
            const yearlyData = {};
            Object.entries(data).forEach(function(item) {
                const period = item[0];
                const value = item[1];
                const parts = period.split('_');
                const year = parts[0];
                const quarter = parts[1];
                if (!yearlyData[year]) yearlyData[year] = {};
                yearlyData[year][quarter] = value;
            });

            const years = Object.keys(yearlyData).sort();
            const quarters = ['1T', '2T', '3T', '4T'];

            // Calcular maior e menor valor por ano (para as setas)
            const yearStats = {};
            years.forEach(function(year) {
                const values = Object.values(yearlyData[year]).filter(function(v) {
                    return v !== undefined && v !== null && !isNaN(v);
                });
                if (values.length > 0) {
                    yearStats[year] = {
                        max: Math.max.apply(Math, values),
                        min: Math.min.apply(Math, values)
                    };
                }
            });

            // Calcular maior e menor valor de TODA a série histórica (para as barras)
            const allValues = [];
            Object.keys(data).forEach(function(key) {
                const value = data[key];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min.apply(Math, allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max.apply(Math, allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }

            const series = [];
            years.forEach(function(year) {
                quarters.forEach(function(quarter) {
                    const value = yearlyData[year] && yearlyData[year][quarter];
                    if (value !== undefined && value !== null) {
                        series.push({ year: year, quarter: quarter, value: value });
                    }
                });
            });

            let prevValue = null;
            series.forEach(function(point, idx) {
                if (idx === 0) {
                    point.extraClass = 'positive';
                } else {
                    if (point.value > prevValue) point.extraClass = 'positive';
                    else if (point.value < prevValue) point.extraClass = 'negative';
                    else point.extraClass = 'neutral';
                }
                prevValue = point.value;
            });

            let tableId = 'table_' + title.replace(/\s+/g, '_');

            let tableHtml = '<div class="table-card">';
            tableHtml += '<div class="table-header">';
            tableHtml += '<div class="table-title">' + title + '</div>';
            tableHtml += '</div>';
            tableHtml += '<table id="' + tableId + '" class="data-table quarterly-table">';
            tableHtml += '<thead><tr><th></th>';

            years.forEach(function(year) {
                const hasIncompleteQuarter = quarters.some(function(quarter) {
                    const quarterKey = year + '_' + quarter;
                    return isIncompleteQuarter(quarterKey, currentInfo);
                });
                tableHtml += '<th>' + year + (hasIncompleteQuarter ? ' *' : '') + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';

            quarters.forEach(function(quarter) {
                // Verificar se este trimestre está incompleto em algum ano
                let isQuarterIncomplete = false;
                years.forEach(function(year) {
                    const quarterKey = year + '_' + quarter;
                    if (isIncompleteQuarter(quarterKey, currentInfo)) {
                        isQuarterIncomplete = true;
                    }
                });
                
                // Adicionar asterisco no label do trimestre se incompleto
                const quarterLabel = quarter + (isQuarterIncomplete ? ' *' : '');
                tableHtml += '<tr><td>' + quarterLabel + '</td>';

                years.forEach(function(year) {
                    const value = yearlyData[year] && yearlyData[year][quarter];
                    let displayValue = '';
                    let extraClass = '';

                    if (value !== undefined && value !== null) {
                        if (isValue) {
                            displayValue = value.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        } else {
                            const valueInMillions = value / 1000000;
                            displayValue = valueInMillions.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }

                        // Adicionar indicadores de máximo e mínimo (por ano)
                        let indicator = '';
                        if (yearStats[year]) {
                            if (value === yearStats[year].max) {
                                indicator = ' <span style="color: #555;">▲</span>';
                            } else if (value === yearStats[year].min) {
                                indicator = ' <span style="color: #555;">▼</span>';
                            }
                        }

                        const point = series.find(function(p) { return p.year === year && p.quarter === quarter; });
                        extraClass = point ? point.extraClass : '';
                        
                        // Calcular largura da barra baseada na série completa
                        const barWidth = getBarWidth(value);

                        tableHtml += '<td class="' + extraClass + '">';
                        tableHtml += '<div style="position: relative; padding: 4px 8px; border-radius: 4px;">';
                        tableHtml += '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth.toFixed(2) + '%; ';
                        tableHtml += 'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ';
                        tableHtml += 'border-radius: 4px; z-index: 0;"></div>';
                        tableHtml += '<div style="position: relative; z-index: 1;">' + displayValue + indicator + '</div>';
                        tableHtml += '</div>';
                        tableHtml += '</td>';
                    } else {
                        tableHtml += '<td></td>';
                    }
                });

                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';

            if (series.length > 1) {
                const lastPoint = series[series.length - 1];
                const prevPoint = series.length > 1 ? series[series.length - 2] : null;

                let prevYearPoint = null;
                for (let i = series.length - 1; i >= 0; i--) {
                    if (series[i].quarter === lastPoint.quarter &&
                        parseInt(series[i].year, 10) === parseInt(lastPoint.year, 10) - 1) {
                        prevYearPoint = series[i];
                        break;
                    }
                }

                const pct = function(a, b) { 
                    return (b === 0 || b == null) ? null : ((a / b) - 1) * 100; 
                };
                
                const spanPct = function(diff) {
                    if (diff === null) return '<span class="neutral">-</span>';
                    const cls = diff > 0 ? 'positive' : diff < 0 ? 'negative' : 'neutral';
                    const sign = diff > 0 ? '+' : '';
                    return '<span class="' + cls + '">' + sign + diff.toFixed(1).replace('.', ',') + '%</span>';
                };

                const parts = [];
                if (prevPoint) {
                    const d1 = pct(lastPoint.value, prevPoint.value);
                    parts.push(lastPoint.quarter + '/' + lastPoint.year + ' - ' + prevPoint.quarter + '/' + prevPoint.year + ': ' + spanPct(d1));
                }
                if (prevYearPoint) {
                    const d2 = pct(lastPoint.value, prevYearPoint.value);
                    parts.push(lastPoint.quarter + '/' + lastPoint.year + ' - ' + prevYearPoint.quarter + '/' + prevYearPoint.year + ': ' + spanPct(d2));
                }

                if (parts.length) {
                    tableHtml += '<div class="variation-info">' + parts.join(' | ') + '</div>';
                }
            }

            const hasIncompleteData = years.some(function(year) {
                return quarters.some(function(quarter) {
                    const quarterKey = year + '_' + quarter;
                    return isIncompleteQuarter(quarterKey, currentInfo);
                });
            });

            if (hasIncompleteData) {
                const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                const lastAvailableMonth = currentInfo.maxMonth;
                const lastAvailableYear = currentInfo.maxYear;
                const monthLabel = lastAvailableMonth ? monthNames[lastAvailableMonth - 1] : '';

                tableHtml += '<div style="font-size: 12px; color: #1976D2; margin-top: 10px; padding: 8px; background-color: #E3F2FD; border-radius: 4px;">';
                tableHtml += '* Trimestre incompleto (dados até ' + monthLabel + '/' + lastAvailableYear + ')';
                tableHtml += '</div>';
            }

            tableHtml += '</div>';
            return tableHtml;
        }

        function createYearlyTableMoney(title, data, isValue) {
            isValue = isValue || false;
            if (Object.keys(data).length === 0) {
                return '<div class="table-card"><div class="table-title">' + title + '</div><div class="no-data">Nenhum dado disponível</div></div>';
            }

            const currentInfo = getCurrentPeriodInfo();
            const years = Object.keys(data).sort();

            // Calcular maior e menor valor da série (para as setas)
            const allValues = [];
            Object.keys(data).forEach(function(year) {
                const value = data[year];
                if (value !== undefined && value !== null && !isNaN(value)) {
                    allValues.push(value);
                }
            });
            const seriesMin = allValues.length > 0 ? Math.min.apply(Math, allValues) : 0;
            const seriesMax = allValues.length > 0 ? Math.max.apply(Math, allValues) : 0;
            
            function getBarWidth(value) {
                if (seriesMax === seriesMin) return 50;
                return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
            }

            let tableId = 'table_' + title.replace(/\s+/g, '_');

            let tableHtml = '<div class="table-card">';
            tableHtml += '<div class="table-header">';
            tableHtml += '<div class="table-title">' + title + '</div>';
            tableHtml += '</div>';
            tableHtml += '<table id="' + tableId + '" class="data-table yearly-table">';
            tableHtml += '<thead><tr><th>Ano</th><th>Valor</th>';

            if (years.length > 1) {
                tableHtml += '<th>Var %</th>';
            }

            tableHtml += '</tr></thead><tbody>';

            years.forEach(function(year, index) {
                const value = data[year];
                const isIncompleteYearData = isIncompleteYear(year, currentInfo);
                let displayValue = '';
                let variationText = '';
                let valueClass = 'neutral';

                if (value !== undefined && value !== null) {
                    if (isValue) {
                        displayValue = value.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                    } else {
                        const valueInMillions = value / 1000000;
                        displayValue = valueInMillions.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                    }

                    // Adicionar setas para maior e menor valor
                    let indicator = '';
                    if (value === seriesMax) {
                        indicator = ' <span style="color: #555;">▲</span>';
                    } else if (value === seriesMin) {
                        indicator = ' <span style="color: #555;">▼</span>';
                    }
                    displayValue += indicator;

                    if (index === 0) {
                        valueClass = 'positive';
                    } else {
                        const prevYear = years[index - 1];
                        const prevValue = data[prevYear];
                        if (prevValue !== undefined && prevValue !== null && prevValue !== 0) {
                            if (value > prevValue) valueClass = 'positive';
                            else if (value < prevValue) valueClass = 'negative';
                        }
                    }
                }

                if (index > 0 && years.length > 1) {
                    const prevYear = years[index - 1];
                    const prevValue = data[prevYear];
                    if (prevValue !== undefined && prevValue !== null && !isNaN(prevValue) && prevValue !== 0 &&
                        value !== undefined && value !== null && !isNaN(value)) {
                        const variation = ((value - prevValue) / prevValue) * 100;
                        const sign = variation >= 0 ? '+' : '';
                        variationText = sign + variation.toFixed(1).replace('.', ',') + '%';
                    } else {
                        variationText = '-';
                    }
                } else if (years.length > 1) {
                    variationText = '-';
                }

                const yearLabel = isIncompleteYearData ? year + ' *' : year;

                tableHtml += '<tr><td>' + yearLabel + '</td>';
                
                // Célula com valor e barra
                const barWidth = getBarWidth(value);
                tableHtml += '<td class="' + valueClass + '">';
                tableHtml += '<div style="position: relative; padding: 4px 8px; border-radius: 4px;">';
                tableHtml += '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth.toFixed(2) + '%; ';
                tableHtml += 'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ';
                tableHtml += 'border-radius: 4px; z-index: 0;"></div>';
                tableHtml += '<div style="position: relative; z-index: 1;">' + displayValue + '</div>';
                tableHtml += '</div>';
                tableHtml += '</td>';

                // Coluna de variação (SEM setas)
                if (years.length > 1) {
                    if (variationText !== '-') {
                        const cleaned = variationText.replace('%', '').replace('+', '').replace('*', '').replace(',', '.').trim();
                        const variation = parseFloat(cleaned);
                        let cssClass = 'neutral';
                        if (!isNaN(variation)) {
                            if (variation > 0) cssClass = 'positive';
                            else if (variation < 0) cssClass = 'negative';
                        }
                        tableHtml += '<td class="' + cssClass + '">' + variationText + '</td>';
                    } else {
                        tableHtml += '<td>' + variationText + '</td>';
                    }
                }

                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';

            const hasIncompleteData = years.some(function(year) { return isIncompleteYear(year, currentInfo); });
            if (hasIncompleteData) {
                const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                const lastAvailableMonth = currentInfo.maxMonth;
                const lastAvailableYear = currentInfo.maxYear;
                const monthLabel = lastAvailableMonth ? monthNames[lastAvailableMonth - 1] : '';

                tableHtml += '<div style="font-size: 12px; color: #1976D2; margin-top: 10px; padding: 8px; background-color: #E3F2FD; border-radius: 4px;">';
                tableHtml += '* Ano incompleto (dados até ' + monthLabel + '/' + lastAvailableYear + ')';
                tableHtml += '</div>';
            }

            tableHtml += '</div>';
            return tableHtml;
        }

        function updateTables(data) {
            if (data.length === 0) {
                document.getElementById('tablesContainer').innerHTML = '<div class="no-data">Nenhum dado disponível</div>';
                return;
            }

            // Cálculos existentes (Tabelas 1-12)
            const ivvPeriods = calculateIVVPeriodAggregations(data);
            const ofertasPeriods = calculatePeriodAggregations(data, ['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS'], true);
            const vendasPeriods = calculatePeriodAggregations(data, ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS'], false);
            const lancamentosPeriods = calculatePeriodAggregations(data, ['OFERTADOS LANCAMENTOS'], false);
            
            // Novos cálculos (Tabelas 13-33)
            const ofertaAreaPeriods = calculateAreaPeriodAggregations(data, ['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS'], true);
            const vendaAreaPeriods = calculateAreaPeriodAggregations(data, ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS'], false);
            const ofertaValorPonderadoPeriods = calculateValorPonderadoPeriodAggregations(data, ['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS']);
            const vendaValorPonderadoPeriods = calculateValorPonderadoPeriodAggregations(data, ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS']);
            const vglPeriods = calculateVGLVGVPeriodAggregations(data, ['OFERTADOS LANCAMENTOS']);
            const vgvPeriods = calculateVGLVGVPeriodAggregations(data, ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS']);
            const distratosPeriods = calculatePeriodAggregations(data, ['DISTRATO'], false);
            
            let tablesHtml = '';
            
            // Tabelas 1-3: IVV (percentuais - 1 casa decimal)
            tablesHtml += createTable('Tabela 1 – IVV Mensal', ivvPeriods.monthly, true);
            tablesHtml += createQuarterlyTable('Tabela 2 – IVV Trimestral', ivvPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 3 – IVV Anual', ivvPeriods.yearly);
            
            // Tabelas 4-6: Ofertas (Unidades - sem casas decimais)
            tablesHtml += createTable('Tabela 4 – Ofertas Mensais (Unidades)', ofertasPeriods.monthly, false);
            tablesHtml += createQuarterlyTable('Tabela 5 – Ofertas Trimestrais (Unidades)', ofertasPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 6 – Ofertas Anuais (Unidades)', ofertasPeriods.yearly);
            
            // Tabelas 7-9: Vendas (Unidades - sem casas decimais)
            tablesHtml += createTable('Tabela 7 – Vendas Mensais (Unidades)', vendasPeriods.monthly, false);
            tablesHtml += createQuarterlyTable('Tabela 8 – Vendas Trimestrais (Unidades)', vendasPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 9 – Vendas Anuais (Unidades)', vendasPeriods.yearly);
            
            // Tabelas 10-12: Lançamentos (Unidades - sem casas decimais)
            tablesHtml += createTable('Tabela 10 – Lançamentos Mensais (Unidades [Empreendimentos])', lancamentosPeriods.monthly, false, projectsCount.residencial, projectsCountEmpreendimentos.residencial);
            tablesHtml += createQuarterlyTable('Tabela 11 – Lançamentos Trimestrais (Unidades [Empreendimentos])', lancamentosPeriods.quarterly, projectsCount.residencial_quarterly, projectsCountEmpreendimentos.residencial_quarterly);
            tablesHtml += createYearlyTable('Tabela 12 – Lançamentos Anuais (Unidades [Empreendimentos])', lancamentosPeriods.yearly, projectsCount.residencial_yearly, projectsCountEmpreendimentos.residencial_yearly);
            
            // Tabelas 13-15: Ofertas (m² - sem casas decimais)
            tablesHtml += createTable('Tabela 13 – Oferta Mensal (m²)', ofertaAreaPeriods.monthly, false);
            tablesHtml += createQuarterlyTable('Tabela 14 – Oferta Trimestral (m²)', ofertaAreaPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 15 – Oferta Anual (m²)', ofertaAreaPeriods.yearly);
            
            // Tabelas 16-18: Vendas (m² - sem casas decimais)
            tablesHtml += createTable('Tabela 16 – Venda Mensal (m²)', vendaAreaPeriods.monthly, false);
            tablesHtml += createQuarterlyTable('Tabela 17 – Venda Trimestral (m²)', vendaAreaPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 18 – Venda Anual (m²)', vendaAreaPeriods.yearly);
            
            // Tabelas 19-21: Ofertas Valor Médio Ponderado (R$/m² - 2 casas decimais)
            tablesHtml += createTableMoney('Tabela 19 – Oferta Valor Médio Ponderado Mensal (R$/m²)', ofertaValorPonderadoPeriods.monthly, true);
            tablesHtml += createQuarterlyTableMoney('Tabela 20 – Oferta Valor Médio Ponderado Trimestral (R$/m²)', ofertaValorPonderadoPeriods.quarterly, true);
            tablesHtml += createYearlyTableMoney('Tabela 21 – Oferta Valor Médio Ponderado Anual (R$/m²)', ofertaValorPonderadoPeriods.yearly, true);
            
            // Tabelas 22-24: Vendas Valor Médio Ponderado (R$/m² - 2 casas decimais)
            tablesHtml += createTableMoney('Tabela 22 – Venda Valor Médio Ponderado Mensal (R$/m²)', vendaValorPonderadoPeriods.monthly, true);
            tablesHtml += createQuarterlyTableMoney('Tabela 23 – Venda Valor Médio Ponderado Trimestral (R$/m²)', vendaValorPonderadoPeriods.quarterly, true);
            tablesHtml += createYearlyTableMoney('Tabela 24 – Venda Valor Médio Ponderado Anual (R$/m²)', vendaValorPonderadoPeriods.yearly, true);
            
            // Tabelas 25-27: VGL (R$ Milhões - 2 casas decimais)
            tablesHtml += createTableMoney('Tabela 25 – VGL Mensal (R$ Milhões)', vglPeriods.monthly, false);
            tablesHtml += createQuarterlyTableMoney('Tabela 26 – VGL Trimestral (R$ Milhões)', vglPeriods.quarterly, false);
            tablesHtml += createYearlyTableMoney('Tabela 27 – VGL Anual (R$ Milhões)', vglPeriods.yearly, false);
            
            // Tabelas 28-30: VGV (R$ Milhões - 2 casas decimais)
            tablesHtml += createTableMoney('Tabela 28 – VGV Mensal (R$ Milhões)', vgvPeriods.monthly, false);
            tablesHtml += createQuarterlyTableMoney('Tabela 29 – VGV Trimestral (R$ Milhões)', vgvPeriods.quarterly, false);
            tablesHtml += createYearlyTableMoney('Tabela 30 – VGV Anual (R$ Milhões)', vgvPeriods.yearly, false);
            
            // Tabelas 31-33: Distratos (Unidades - sem casas decimais)
            tablesHtml += createTable('Tabela 31 – Distratos Mensais (Unidades)', distratosPeriods.monthly, false);
            tablesHtml += createQuarterlyTable('Tabela 32 – Distratos Trimestrais (Unidades)', distratosPeriods.quarterly);
            tablesHtml += createYearlyTable('Tabela 33 – Distratos Anuais (Unidades)', distratosPeriods.yearly);

            document.getElementById('tablesContainer').innerHTML = tablesHtml;
            // Categoriza as tabelas após geração com timeout para garantir renderização
            setTimeout(function() {
                if (typeof assignTableCategories === 'function') {
                    assignTableCategories();
                }
                applyColoringToTableCells();
                
                // Após categorizar, aplicar filtro da categoria ativa ou primeira categoria se estivermos em residencial/comercial
                if ((currentView === 'residencial' || currentView === 'comercial') && viewCategories[currentView] && viewCategories[currentView].length > 0) {
                    // Se já existe uma categoria ativa definida, usar ela; senão usar a primeira
                    const categoryToShow = currentCategory && viewCategories[currentView].includes(currentCategory) 
                        ? currentCategory 
                        : viewCategories[currentView][0];
                    
                    console.log('Aplicando filtro para categoria (preservando se ativa):', categoryToShow, 'currentCategory era:', currentCategory);
                    showCategory(categoryToShow);
                }
            }, 50);
        }

        function applyColoringToTableCells() {
            const tables = document.querySelectorAll(".data-table");

            tables.forEach(function(table) {
                const rows = Array.from(table.querySelectorAll("tbody tr:not(.variation-row)"));
                if (rows.length === 0) return;

                const numCols = rows[0].children.length;
                
                // Para cada coluna (ano), coletar todos os períodos em ordem cronológica
                const allPeriods = [];
                
                for (let col = 1; col < numCols; col++) {
                    const yearHeader = table.querySelector('thead tr th:nth-child(' + (col + 1) + ')').textContent.replace(' *', '');
                    
                    for (let row = 0; row < rows.length; row++) {
                        const cell = rows[row].children[col];
                        if (!cell) continue;
                        
                        const monthName = rows[row].children[0].textContent;
                        
                        // Converter nome do mês para número
                        const monthMap = {
                            'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04',
                            'Mai': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
                            'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
                        };
                        
                        const monthNum = monthMap[monthName];
                        if (!monthNum) continue;
                        
                        const period = parseInt(yearHeader + monthNum);
                        const text = cell.textContent.replace(/\*/g, '').replace(/\./g, '').replace(',', '.').replace('%', '').trim();
                        const value = parseFloat(text);
                        
                        if (!isNaN(value)) {
                            allPeriods.push({
                                period: period,
                                value: value,
                                cell: cell,
                                col: col,
                                row: row
                            });
                        }
                    }
                }
                
                // Ordenar todos os períodos cronologicamente
                allPeriods.sort(function(a, b) { return a.period - b.period; });
                
                // Aplicar coloração baseada na série temporal contínua
                for (let i = 0; i < allPeriods.length; i++) {
                    const currentPeriod = allPeriods[i];
                    
                    // Remover classes antigas
                    currentPeriod.cell.classList.remove('positive', 'negative', 'neutral');
                    
                    if (i === 0) {
                        // Primeiro período sempre neutro/positivo
                        currentPeriod.cell.classList.add('positive');
                    } else {
                        const prevPeriod = allPeriods[i - 1];
                        
                        if (currentPeriod.value > prevPeriod.value) {
                            currentPeriod.cell.classList.add('positive');
                        } else if (currentPeriod.value < prevPeriod.value) {
                            currentPeriod.cell.classList.add('negative');
                        } else {
                            currentPeriod.cell.classList.add('neutral');
                        }
                    }
                }
            });
        }

        document.addEventListener("DOMContentLoaded", function() {
            // Mostrar o dashboard
            const container = document.getElementById('dashboardContainer');
            if (container) container.style.display = 'block';
            
            // Apenas popular filtros e atualizar tabelas se não for crosstabs
            if (currentView !== 'crosstabs') {
                populateFilters();
                
                // Verificar se há dados antes de tentar atualizar tabelas
                if (rawData && rawData[currentView] && rawData[currentView].length > 0) {
                    updateTables(rawData[currentView]);
                } else {
                    // Se não há dados, mostrar mensagem ou dados de exemplo
                    document.getElementById('tablesContainer').innerHTML = '<div class="no-data">Aguardando carregamento dos dados...</div>';
                }
                
                if (typeof buildCategoryNav === 'function') {
                    buildCategoryNav();
                }
            }
        });
        
// === Trend coloring helpers (safe) ===
function parseNumberBR(text) {
    if (!text) return NaN;
    // remove footnote marker and percent sign
    let t = String(text).replace('*','').replace('%','').trim();
    // remove thousand separators and use dot as decimal
    t = t.replace(/\./g, '').replace(',', '.');
    const v = parseFloat(t);
    return isNaN(v) ? NaN : v;
}

function applyTrendColorsQuarterly() {
    document.querySelectorAll('table.quarterly-table').forEach(table => {
        const rows = table.tBodies[0] ? Array.from(table.tBodies[0].rows) : [];
        rows.forEach(tr => {
            // skip label cell (index 0), iterate by columns across years
            const tds = Array.from(tr.cells).slice(1);
            let prev = null;
            tds.forEach(td => {
                const val = parseNumberBR(td.textContent);
                if (!isNaN(val)) {
                    if (prev === null) {
                        td.classList.add('positive');
                    } else if (val > prev) {
                        td.classList.add('positive');
                    } else if (val < prev) {
                        td.classList.add('negative');
                    } else {
                        td.classList.add('neutral');
                    }
                    prev = val;
                }
            });
        });
    });
}

        /* ======== NOVAS FUNÇÕES DE NAVEGAÇÃO E CROSSTABS ======== */
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainContainer = document.getElementById('mainContainer');
            const filtersContainer = document.querySelector('.filters-container');
            const logoImg = sidebar ? sidebar.querySelector('.logo-container img') : null;
            
            if (sidebar && logoImg) {
                const wasCollapsed = sidebar.classList.contains('collapsed');
                sidebar.classList.toggle('collapsed');
                
                // Trocar logo baseado no NOVO estado (após o toggle)
                // CORREÇÃO: Usar sempre a mesma logo, apenas redimensionar
                if (sidebar.classList.contains('collapsed')) {
                    // Retraído: manter mesma logo, apenas redimensionar via CSS
                    closeAllSubmenus();
                } else {
                    // Expandido: manter mesma logo
                }
                
                // Debug para verificar
            }
            
            // Aplicar classes collapsed de forma sincronizada
            if (mainContainer) {
                mainContainer.classList.toggle('collapsed');
            }
            
            if (filtersContainer) {
                filtersContainer.classList.toggle('collapsed');
            }
            
            // REDIMENSIONAMENTO SIMPLIFICADO: Uma única tentativa bem executada
            setTimeout(() => {
                
                // 1. Disparar evento de resize global
                window.dispatchEvent(new Event('resize'));
                
                // 2. Redimensionar gráficos Chart.js
                if (window.Chart && window.Chart.instances) {
                    Object.values(window.Chart.instances).forEach(chart => {
                        if (chart && typeof chart.resize === 'function') {
                            chart.resize();
                            console.log('Gráfico redimensionado:', chart.canvas.id || 'sem ID');
                        }
                    });
                }
                
                // 3. Redimensionar via variáveis globais conhecidas
                const globalCharts = ['chartInstance', 'economicChart', 'chartInsights'];
                globalCharts.forEach(varName => {
                    if (typeof window[varName] !== 'undefined' && window[varName] && window[varName].resize) {
                        window[varName].resize();
                        console.log(`Gráfico global redimensionado: ${varName}`);
                    }
                });
                
                // 4. Forçar reflow simples dos containers principais
                const containers = document.querySelectorAll('.main-container, .chart-wrapper, .table-wrapper');
                containers.forEach(container => {
                    container.style.width = '';
                    container.offsetWidth; // Trigger reflow
                });
                
                console.log('Redimensionamento concluído!');
            }, 350);
        }
        
        // Função para testar conectividade com diferentes CDNs
        function testCDNConnectivity() {
            const testUrls = [
                'https://raw.githubusercontent.com/aag1974/dashboard-ivv/main/logo.png',
                'https://cdn.jsdelivr.net/gh/aag1974/dashboard-ivv@main/logo.png'
            ];
            
            console.log('🔍 Testando conectividade com CDNs...');
            
            testUrls.forEach((url, index) => {
                const img = new Image();
                img.onload = function() {
                    console.log(`✅ CDN ${index + 1} disponível:`, url);
                };
                img.onerror = function() {
                    console.log(`❌ CDN ${index + 1} indisponível:`, url);
                };
                img.src = url + '?t=' + Date.now(); // Cache busting
            });
        }
        
        // Função para monitoramento contínuo da logo
        function startLogoMonitoring() {
            setInterval(() => {
                const sidebar = document.getElementById('sidebar');
                const logoImg = sidebar ? sidebar.querySelector('.logo-container img') : null;
                
                if (logoImg) {
                    // Verificar se a logo está carregada corretamente
                    const isLogoValid = logoImg.complete && 
                                       logoImg.naturalHeight > 0 && 
                                       logoImg.naturalWidth > 0 &&
                                       logoImg.src && 
                                       logoImg.src !== '';
                    
                    if (!isLogoValid) {
                        console.warn('🚨 Logo detectada como inválida, recarregando...');
                        ensureCorrectLogo();
                    }
                }
            }, 30000); // Verificar a cada 30 segundos
        }
        
        // Função para garantir logo correta na inicialização
        function ensureCorrectLogo() {
            const sidebar = document.getElementById('sidebar');
            const logoImg = sidebar ? sidebar.querySelector('.logo-container img') : null;
            
            if (sidebar && logoImg) {
                // Se a logo já está carregada, não fazer nada
                if (logoImg.complete && logoImg.naturalHeight > 0) {
                    console.log('✅ Logo já carregada:', logoImg.src);
                    return;
                }
                
                console.log('🔄 Carregando logo...');
                
                // URLs de fallback
                const logoUrls = [
                    'https://raw.githubusercontent.com/aag1974/dashboard-ivv/main/logo.png',
                    'https://cdn.jsdelivr.net/gh/aag1974/dashboard-ivv@main/logo.png'
                ];
                
                let currentUrlIndex = 0;
                
                function tryLoadLogo() {
                    if (currentUrlIndex >= logoUrls.length) {
                        console.error('❌ Todas as URLs de logo falharam.');
                        return;
                    }
                    
                    logoImg.src = logoUrls[currentUrlIndex];
                    logoImg.alt = 'Logo Opiniao';
                }
                
                // Listener de erro - tenta próxima URL
                logoImg.onerror = function() {
                    console.error(`❌ Erro na logo (tentativa ${currentUrlIndex + 1})`);
                    currentUrlIndex++;
                    if (currentUrlIndex < logoUrls.length) {
                        setTimeout(tryLoadLogo, 100);
                    }
                };
                
                // Listener de sucesso
                logoImg.onload = function() {
                    console.log('✅ Logo carregada!');
                };
                
                // Iniciar carregamento
                tryLoadLogo();
            }
        }
        
        // Função para clique na logo - abre sidebar se estiver retraída
        function logoClick() {
            const sidebar = document.getElementById('sidebar');
            
            // Se a sidebar estiver retraída, abrir ela
            if (sidebar && sidebar.classList.contains('collapsed')) {
                console.log('Logo clicada: Abrindo sidebar...');
                toggleSidebar();
            }
            // Se estiver aberta, não fazer nada (logo não é funcional quando expandida)
        }
        
        // Função inteligente para cliques nos ícones das views
        function handleViewClick(view, event) {
            const sidebar = document.getElementById('sidebar');
            
            // Se a sidebar estiver retraída, apenas abrir ela
            if (sidebar && sidebar.classList.contains('collapsed')) {
                console.log(`Ícone ${view} clicado: Abrindo sidebar...`);
                toggleSidebar();
                return; // Não executar ação da view ainda
            }
            
            // Se sidebar estiver aberta, executar ação normal da view
            if (view === 'residencial' || view === 'comercial' || view === 'crosstabs' || view === 'insights') {
                toggleMainMenu(view, event);
            }
        }
        
        // Nova função para fechar todos os submenus sem afetar a view ativa
        function closeAllSubmenus() {
            // Fechar todos os submenus visuais
            document.querySelectorAll('.submenu-container').forEach(function(container) {
                container.classList.remove('expanded');
            });
            
            // Resetar ícones de expansão
            document.querySelectorAll('.expand-icon').forEach(function(icon) {
                icon.textContent = '▶';
            });
            
            // Remover classe expanded dos itens de menu principal
            document.querySelectorAll('.nav-main .nav-item').forEach(function(item) {
                item.classList.remove('expanded');
            });
            
            // Resetar estado de expansão dos menus
            expandedMenus = {
                residencial: false,
                comercial: false
            };
            
            // IMPORTANTE: NÃO alterar currentView nem currentCategory
            // A view e categoria ativas permanecem as mesmas, apenas os submenus ficam fechados
            console.log('Submenus fechados. View ativa mantida:', currentView, 'Categoria ativa mantida:', currentCategory);
        }

        function buildCategoryNav() {
            const nav = document.getElementById('categoryNav');
            if (!nav) return;
            
            nav.innerHTML = '';
            
            // Usar apenas para crosstabs (insights agora usa populateSubmenu)
            if (currentView === 'crosstabs') {
                const cats = viewCategories[currentView] || [];
                cats.forEach(function(cat, idx) {
                    const li = document.createElement('li');
                    li.className = 'nav-item';
                    li.setAttribute('data-category', cat);
                    li.onclick = function() { 
                        // Scroll to top ao clicar em categoria
                        const mainContainer = document.getElementById('mainContainer');
                        if (mainContainer) {
                            mainContainer.scrollTop = 0;
                        }
                        
                        // Scroll to top da janela principal
                        window.scrollTo(0, 0);
                        
                        // Scroll to top do body
                        document.body.scrollTop = 0;
                        document.documentElement.scrollTop = 0;
                        
                        const tablesContainer = document.getElementById('tablesContainer');
                        if (tablesContainer) {
                            tablesContainer.scrollTop = 0;
                        }
                        
                        const crossTablesContainer = document.getElementById('crossTablesContainer');
                        if (crossTablesContainer) {
                            crossTablesContainer.scrollTop = 0;
                        }
                        
                        showCategory(cat); 
                    };
                    li.innerHTML = '<span class="text">' + getFriendlyName(cat) + '</span>';
                    if (idx === 0) li.classList.add('active');
                    nav.appendChild(li);
                });
                if (cats.length > 0) {
                    // Se já existe uma categoria ativa definida, usar ela; senão usar a primeira
                    const categoryToShow = currentCategory && cats.includes(currentCategory) 
                        ? currentCategory 
                        : cats[0];
                    
                    console.log('buildCategoryNav: Aplicando categoria (preservando se ativa):', categoryToShow);
                    showCategory(categoryToShow);
                }
            }
        }

        function assignTableCategories() {
            console.log('assignTableCategories: Iniciando categorização das tabelas');
            const cards = document.querySelectorAll('#tablesContainer .table-card');
            console.log('Total de cards encontrados:', cards.length);
            
            cards.forEach(function(card, index) {
                const titleEl = card.querySelector('.table-title');
                if (!titleEl) return;
                
                const rawTitle = titleEl.textContent || '';
                const title = rawTitle.toLowerCase();
                let cat = '';
                
                if (title.includes('ivv')) {
                    cat = 'ivv';
                } else if (title.includes('oferta') && title.includes('valor') && title.includes('ponderado')) {
                    // Ofertas valor ponderado (prioridade sobre m²)
                    cat = 'valor_ponderado_oferta';
                } else if (title.includes('venda') && title.includes('valor') && title.includes('ponderado')) {
                    // Vendas valor ponderado (prioridade sobre m²)
                    cat = 'valor_ponderado_venda';
                } else if (title.includes('oferta') && title.includes('m²') && !title.includes('valor')) {
                    // Ofertas em m² (excluindo valor ponderado)
                    cat = 'oferta_m2';
                } else if (title.includes('venda') && title.includes('m²') && !title.includes('valor')) {
                    // Vendas em m² (excluindo valor ponderado)
                    cat = 'venda_m2';
                } else if (title.includes('oferta') && !title.includes('m²') && !title.includes('valor')) {
                    // Ofertas em unidades (sem m² e sem valor)
                    cat = 'oferta';
                } else if (title.includes('venda') && !title.includes('m²') && !title.includes('valor')) {
                    // Vendas em unidades (sem m² e sem valor)
                    cat = 'venda';
                } else if (title.includes('lanç') || title.includes('lanc')) {
                    cat = 'lancamentos';
                } else if (title.includes('vgl')) {
                    cat = 'vgl';
                } else if (title.includes('vgv')) {
                    cat = 'vgv';
                } else if (title.includes('distrato')) {
                    cat = 'distratos';
                }
                
                if (cat) {
                    card.setAttribute('data-category', cat);
                    console.log(`Tabela ${index + 1}: "${rawTitle}" → categoria: ${cat}`);
                } else {
                    console.warn(`Tabela ${index + 1}: "${rawTitle}" → SEM CATEGORIA!`);
                }
            });
            
            console.log('assignTableCategories: Categorização concluída');
        }

        function showCategory(cat) {
            console.log('showCategory chamada para:', cat);
            
            // Atualizar categoria ativa
            currentCategory = cat;
            
            // Scroll to top da área principal
            const mainContainer = document.getElementById('mainContainer');
            if (mainContainer) {
                mainContainer.scrollTop = 0;
            }
            
            // Scroll to top da janela principal
            window.scrollTo(0, 0);
            
            // Scroll to top do body
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
            
            // Scroll to top da área de tabelas
            const tablesContainer = document.getElementById('tablesContainer');
            if (tablesContainer) {
                tablesContainer.scrollTop = 0;
            }
            
            // Scroll to top da área de crosstabs
            const crossTablesContainer = document.getElementById('crossTablesContainer');
            if (crossTablesContainer) {
                crossTablesContainer.scrollTop = 0;
            }
            
            // destaca categoria no menu
            document.querySelectorAll('#categoryNav li, .submenu-container li').forEach(function(item) {
                if (item.getAttribute('data-category') === cat) item.classList.add('active');
                else item.classList.remove('active');
            });
            
            if (currentView === 'crosstabs') {
                // cross view: mostrar grupos cruzados
                document.querySelectorAll('#crossTablesContainer .cross-group').forEach(function(group) {
                    if (group.getAttribute('data-category') === cat) group.style.display = 'block';
                    else group.style.display = 'none';
                });
            } else if (currentView === 'insights') {
                // insights view: mostrar cards específicos
                const allCards = document.querySelectorAll('#tablesContainer .insight-card');
                
                allCards.forEach(function(card) {
                    const titleEl = card.querySelector('.insight-title');
                    if (!titleEl) return;
                    
                    const title = titleEl.textContent.toLowerCase();
                    let shouldShow = false;
                    
                    // Lógica de correspondência por categoria para insights
                    switch(cat) {
                        case 'indicadores_economicos':
                            // Mostrar todos os cards individuais (SELIC, IPCA, Juros Reais, INCC-M)
                            shouldShow = title.includes('selic') || 
                                       title.includes('ipca') || 
                                       title.includes('juros reais') || 
                                       title.includes('incc');
                            break;
                        case 'correlacoes':
                            // Mostrar apenas o card com gráfico de correlações
                            shouldShow = title.includes('evolução') || 
                                       title.includes('indicadores econômicos') ||
                                       title.includes('comparativo');
                            break;
                        default:
                            shouldShow = false;
                    }
                    
                    card.style.display = shouldShow ? 'block' : 'none';
                });
            } else {
                // Para residencial/comercial: filtrar tabelas por categoria
                const allTables = document.querySelectorAll('#tablesContainer .table-card');
                console.log('Total de tabelas encontradas:', allTables.length);
                
                let tabelasExibidas = 0;
                allTables.forEach(function(card) {
                    const titleEl = card.querySelector('.table-title');
                    if (!titleEl) return;
                    
                    const title = titleEl.textContent.toLowerCase();
                    let shouldShow = false;
                    
                    // Lógica de correspondência por categoria
                    switch(cat) {
                        case 'ivv':
                            shouldShow = title.includes('ivv');
                            break;
                        case 'oferta':
                            shouldShow = title.includes('oferta') && !title.includes('m²') && !title.includes('valor');
                            break;
                        case 'venda':
                            shouldShow = title.includes('venda') && !title.includes('m²') && !title.includes('valor');
                            break;
                        case 'lancamentos':
                            shouldShow = title.includes('lanç') || title.includes('lanc');
                            break;
                        case 'oferta_m2':
                            shouldShow = title.includes('oferta') && title.includes('m²') && !title.includes('valor');
                            break;
                        case 'venda_m2':
                            shouldShow = title.includes('venda') && title.includes('m²') && !title.includes('valor');
                            break;
                        case 'valor_ponderado_oferta':
                            shouldShow = title.includes('oferta') && title.includes('valor');
                            break;
                        case 'valor_ponderado_venda':
                            shouldShow = title.includes('venda') && title.includes('valor');
                            break;
                        case 'vgl':
                            shouldShow = title.includes('vgl');
                            break;
                        case 'vgv':
                            shouldShow = title.includes('vgv');
                            break;
                        case 'distratos':
                            shouldShow = title.includes('distrato');
                            break;
                        default:
                            shouldShow = false;
                    }
                    
                    if (shouldShow) {
                        card.style.display = 'block';
                        tabelasExibidas++;
                        console.log('Mostrando tabela:', title);
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                console.log('Tabelas exibidas para categoria', cat + ':', tabelasExibidas);
                
                // Se nenhuma tabela foi encontrada, mostrar mensagem
                if (tabelasExibidas === 0) {
                    const noDataDiv = document.createElement('div');
                    noDataDiv.className = 'no-data';
                    noDataDiv.style.cssText = 'padding: 20px; text-align: center; color: #666; font-style: italic;';
                    noDataDiv.textContent = 'Nenhuma tabela encontrada para a categoria: ' + getFriendlyName(cat);
                    
                    // Esconder todas as tabelas e mostrar mensagem
                    allTables.forEach(function(card) {
                        card.style.display = 'none';
                    });
                    
                    // Remover mensagem anterior se existir
                    const existingNoData = document.querySelector('#tablesContainer .no-data');
                    if (existingNoData) {
                        existingNoData.remove();
                    }
                    
                    document.getElementById('tablesContainer').appendChild(noDataDiv);
                } else {
                    // Remover mensagem de "nenhuma tabela" se existir
                    const existingNoData = document.querySelector('#tablesContainer .no-data');
                    if (existingNoData) {
                        existingNoData.remove();
                    }
                }
            }
        }
        
        function initializeMenu() {
            // Expandir residencial por padrão
            const residencialItem = document.querySelector('[data-view="residencial"]');
            if (residencialItem) {
                residencialItem.classList.add('expanded');
                const expandIcon = residencialItem.querySelector('.expand-icon');
                if (expandIcon) expandIcon.textContent = '▼';
                
                const submenuContainer = document.getElementById('submenu-residencial');
                if (submenuContainer) submenuContainer.classList.add('expanded');
                
                populateSubmenu('residencial');
                
                // Forçar carregamento das tabelas após inicialização
                setTimeout(function() {
                    if (rawData && rawData.residencial && rawData.residencial.length > 0) {
                        updateTables(rawData.residencial);
                    } else {
                        // Mostrar que não há dados
                        document.getElementById('tablesContainer').innerHTML = '<div class="no-data" style="padding: 20px; text-align: center; color: #666;">Nenhum dado disponível. Carregue um arquivo Excel para ver as tabelas.</div>';
                    }
                }, 100);
            }
        }
        
        // Inicializar quando o DOM estiver pronto
        document.addEventListener('DOMContentLoaded', function() {
            initializeMenu();
            testCDNConnectivity(); // Testar conectividade com CDNs
            ensureCorrectLogo(); // Garantir que a logo esteja correta imediatamente
            startLogoMonitoring(); // Iniciar monitoramento contínuo da logo
        });

        function generateCrossData(data) {
            console.log('generateCrossData: Processando', data.length, 'registros');
            const result = {
                oferta_quantidade: {},
                venda_quantidade: {},
                valor_ponderado_oferta: {},
                valor_ponderado_venda: {},
                oferta_m2: {},
                venda_m2: {},
                gastos_pos_entrega: {},
                gastos_por_categoria: {}
            };
            const ofertaTypes = ['OFERTADOS DISPONIVEIS', 'OFERTADOS LANCAMENTOS'];
            const vendaTypes = ['VENDIDOS', 'VENDIDOS - LANCADOS E VENDIDOS'];
            
            let processedRows = 0;
            data.forEach(function(row) {
                const bairro = row.BAIRRO || '';
                let quartos = row.QTD_QUARTOS;
                let qVal;
                if (quartos === null || quartos === undefined || quartos === '') {
                    qVal = '';
                } else {
                    const num = parseInt(quartos);
                    qVal = (!isNaN(num) && num >= 4) ? '4+' : String(quartos);
                }
                if (!bairro) return;
                
                processedRows++;
                if (processedRows <= 3) {
                    console.log('Exemplo linha', processedRows + ':', {
                        bairro: bairro,
                        quartos: qVal,
                        ofertaVenda: row.OFERTA_VENDA,
                        quantidade: row.QUANTIDADE,
                        areaQuantidade: row.AREA_QUANTIDADE,
                        areaQuantidadeValor: row.AREA_QUANTIDADE_VALOR
                    });
                }
                if (ofertaTypes.includes(row.OFERTA_VENDA)) {
                    // Quantidade de ofertas
                    if (!result.oferta_quantidade[bairro]) result.oferta_quantidade[bairro] = {};
                    if (!result.oferta_quantidade[bairro][qVal]) result.oferta_quantidade[bairro][qVal] = 0;
                    result.oferta_quantidade[bairro][qVal] += (row.QUANTIDADE || 0);
                    
                    // Valor ponderado de ofertas (mantido)
                    if (!result.valor_ponderado_oferta[bairro]) result.valor_ponderado_oferta[bairro] = {};
                    if (!result.valor_ponderado_oferta[bairro][qVal]) result.valor_ponderado_oferta[bairro][qVal] = { totalValor:0, totalArea:0 };
                    result.valor_ponderado_oferta[bairro][qVal].totalValor += (row.AREA_QUANTIDADE_VALOR || 0);
                    result.valor_ponderado_oferta[bairro][qVal].totalArea += (row.AREA_QUANTIDADE || 0);
                    
                    // Área de ofertas (mantido)
                    if (!result.oferta_m2[bairro]) result.oferta_m2[bairro] = {};
                    if (!result.oferta_m2[bairro][qVal]) result.oferta_m2[bairro][qVal] = 0;
                    result.oferta_m2[bairro][qVal] += (row.AREA_QUANTIDADE || 0);
                }
                if (vendaTypes.includes(row.OFERTA_VENDA)) {
                    // Quantidade de vendas
                    if (!result.venda_quantidade[bairro]) result.venda_quantidade[bairro] = {};
                    if (!result.venda_quantidade[bairro][qVal]) result.venda_quantidade[bairro][qVal] = 0;
                    result.venda_quantidade[bairro][qVal] += (row.QUANTIDADE || 0);
                    
                    // Valor ponderado de vendas (mantido)
                    if (!result.valor_ponderado_venda[bairro]) result.valor_ponderado_venda[bairro] = {};
                    if (!result.valor_ponderado_venda[bairro][qVal]) result.valor_ponderado_venda[bairro][qVal] = { totalValor:0, totalArea:0 };
                    result.valor_ponderado_venda[bairro][qVal].totalValor += (row.AREA_QUANTIDADE_VALOR || 0);
                    result.valor_ponderado_venda[bairro][qVal].totalArea += (row.AREA_QUANTIDADE || 0);
                    
                    // Área de vendas (mantido)
                    if (!result.venda_m2[bairro]) result.venda_m2[bairro] = {};
                    if (!result.venda_m2[bairro][qVal]) result.venda_m2[bairro][qVal] = 0;
                    result.venda_m2[bairro][qVal] += (row.AREA_QUANTIDADE || 0);
                    
                    // Gastos Pós-Entrega baseado em VGV (metodologia CBIC)
                    if (!result.gastos_pos_entrega[bairro]) result.gastos_pos_entrega[bairro] = {};
                    if (!result.gastos_pos_entrega[bairro][qVal]) result.gastos_pos_entrega[bairro][qVal] = 0;
                    
                    // Cálculo baseado na metodologia CBIC com classificação por região:
                    const vgv = row.AREA_QUANTIDADE_VALOR || 0;
                    
                    // Classificação por padrão construtivo das regiões
                    const padraoRegioes = {
                        'Alto': ['NOROESTE', 'SUDOESTE', 'JARDIM BOTÂNICO', 'ASA SUL', 'ASA NORTE', 'LAGO NORTE'],
                        'Médio': ['ÁGUAS CLARAS', 'GUARÁ', 'SOBRADINHO', 'SOBRADINHO II', 'PARK SUL', 'TAGUATINGA'],
                        'Popular': ['CEILÂNDIA', 'PLANALTINA', 'SANTA MARIA', 'GAMA', 'RECANTO DAS EMAS', 'SAMAMBAIA']
                    };
                    
                    function getPadraoRegiao(nomeRegiao) {
                        const regiaoUpper = nomeRegiao.toUpperCase();
                        for (const [padrao, regioes] of Object.entries(padraoRegioes)) {
                            if (regioes.some(r => regiaoUpper.includes(r) || r.includes(regiaoUpper))) {
                                return padrao;
                            }
                        }
                        return 'Médio'; // Padrão default
                    }
                    
                    const padraoRegiao = getPadraoRegiao(bairro);
                    let percentualCBIC = 0.15; // Padrão: Médio (15% VGV)
                    if (padraoRegiao === 'Popular') {
                        percentualCBIC = 0.10; // Popular (10% VGV)
                    } else if (padraoRegiao === 'Alto') {
                        percentualCBIC = 0.25; // Alto (25% VGV)
                    }
                    
                    const gastoPosObra = vgv * percentualCBIC;
                    result.gastos_pos_entrega[bairro][qVal] += gastoPosObra;
                }
            });
            const computeAvg = function(obj) {
                const out = {};
                Object.keys(obj).forEach(function(b) {
                    out[b] = {};
                    Object.keys(obj[b]).forEach(function(q) {
                        const entry = obj[b][q];
                        out[b][q] = entry.totalArea > 0 ? (entry.totalValor / entry.totalArea) : 0;
                    });
                });
                return out;
            };
            const finalResult = {
                oferta_quantidade: result.oferta_quantidade,
                venda_quantidade: result.venda_quantidade,
                valor_ponderado_oferta: computeAvg(result.valor_ponderado_oferta),
                valor_ponderado_venda: computeAvg(result.valor_ponderado_venda),
                oferta_m2: result.oferta_m2,
                venda_m2: result.venda_m2,
                gastos_pos_entrega: result.gastos_pos_entrega,
                gastos_por_categoria: result.gastos_por_categoria,
                // Adicionar dados brutos para cálculo correto dos totais
                _rawOferta: result.valor_ponderado_oferta,
                _rawVenda: result.valor_ponderado_venda
            };
            
            console.log('generateCrossData: Resultado final:', {
                processedRows: processedRows,
                bairrosOfertaQuantidade: Object.keys(finalResult.oferta_quantidade).length,
                bairrosVendaQuantidade: Object.keys(finalResult.venda_quantidade).length,
                bairrosOfertaValorPond: Object.keys(finalResult.valor_ponderado_oferta).length,
                bairrosVendaValorPond: Object.keys(finalResult.valor_ponderado_venda).length,
                bairrosOfertaM2: Object.keys(finalResult.oferta_m2).length,
                bairrosVendaM2: Object.keys(finalResult.venda_m2).length,
                bairrosGastosPosObra: Object.keys(finalResult.gastos_pos_entrega).length,
                amostra: finalResult
            });
            
            return finalResult;
        }

        // ============== FUNÇÕES PARA CROSSTABS ==============
        
        function populateCrossTabsFilters() {
            const data = crossTabsData.residencial || [];
            
            // Popular filtro de período
            const periods = new Set();
            data.forEach(function(row) {
                if (row.ANO_MES) {
                    periods.add(row.ANO_MES);
                }
            });
            
            const sortedPeriods = Array.from(periods).sort(function(a, b) {
                return parseInt(b) - parseInt(a);
            });
            
            const periodoContent = document.getElementById('periodoContent');
            if (!periodoContent) return;
            
            periodoContent.innerHTML = '';
            
            sortedPeriods.forEach(function(period) {
                const div = document.createElement('div');
                div.className = 'dropdown-option';
                
                const radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'periodo';
                radio.value = period;
                radio.onchange = function() { 
                    updatePeriodSelection(); 
                };
                
                const label = document.createElement('label');
                label.textContent = formatPeriodLabel(period);
                
                div.appendChild(radio);
                div.appendChild(label);
                periodoContent.appendChild(div);
            });
            
            // Selecionar primeiro período (mais recente)
            const firstRadio = periodoContent.querySelector('input[type="radio"]');
            if (firstRadio) {
                firstRadio.checked = true;
                updatePeriodSelection();
            }
        }
        
        function formatPeriodLabel(period) {
            if (!period) return 'N/D';
            const str = period.toString().padStart(6, '0');
            const ano = str.substring(0, 4);
            const mes = str.substring(4, 6);
            const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
            return meses[parseInt(mes, 10) - 1] + '/' + ano;
        }
        
        function updatePeriodSelection() {
            const selectedRadio = document.querySelector('#periodoContent input[type="radio"]:checked');
            const periodoText = document.getElementById('periodoText');
            
            if (selectedRadio && periodoText) {
                const label = selectedRadio.parentElement.querySelector('label').textContent;
                periodoText.textContent = label;
            }
            
            if (currentView === 'crosstabs') {
                applyCrossTabsFilters();
            }
        }
        
        function getCrossTabsFilters() {
            const filters = {};
            
            // Período
            const selectedPeriod = document.querySelector('#periodoContent input[type="radio"]:checked');
            if (selectedPeriod) {
                filters.periodo = selectedPeriod.value;
            }
            
            // Faixa de valor
            const faixaCheckboxes = document.querySelectorAll('#faixaValorContent .dropdown-option:not(.select-all) input:checked');
            filters.faixaValor = Array.from(faixaCheckboxes).map(cb => cb.value);
            
            return filters;
        }
        
        function filterCrossTabsData(data, filters) {
            let filteredData = data;
            
            if (filters.periodo) {
                filteredData = filteredData.filter(function(row) {
                    return row.ANO_MES && row.ANO_MES.toString() === filters.periodo.toString();
                });
            }
            
            if (filters.faixaValor && filters.faixaValor.length > 0) {
                filteredData = filteredData.filter(function(row) {
                    return filters.faixaValor.includes(row.Faixa_Valor);
                });
            }
            
            return filteredData;
        }
        
        function applyCrossTabsFilters() {
            const data = crossTabsData.residencial || [];
            const filters = getCrossTabsFilters();
            const filteredData = filterCrossTabsData(data, filters);
            
            console.log('Crosstabs filtros:', filters);
            console.log('Dados filtrados:', filteredData.length, 'de', data.length);
            
            renderCrossTables(filteredData);
            
            // Preservar categoria ativa após aplicar filtros
            if (currentCategory) {
                setTimeout(function() {
                    showCategory(currentCategory);
                }, 100);
            }
        }

        function renderCrossTables(data) {
            const container = document.getElementById('crossTablesContainer');
            if (!container) {
                console.error('crossTablesContainer não encontrado!');
                return;
            }
            container.innerHTML = '';
            container.style.display = 'block';
            document.getElementById('tablesContainer').style.display = 'none';
            
            if (data.length === 0) {
                container.innerHTML = '<div class="no-data" style="padding: 20px; text-align: center;">Nenhum dado disponível para crosstabs</div>';
                return;
            }
            
            const cross = generateCrossData(data);
            console.log('generateCrossData resultado:', cross);
            
            const cats = ['oferta_quantidade','venda_quantidade','valor_ponderado_oferta','valor_ponderado_venda','oferta_m2','venda_m2','gastos_pos_entrega','gastos_por_categoria'];
            cats.forEach(function(cat, index) {
                console.log('Processando categoria:', cat);
                const tableData = cross[cat];
                
                // Para tabelas especiais, não dependemos de tableData
                const isSpecialTable = (cat === 'gastos_pos_entrega' || cat === 'gastos_por_categoria');
                
                // Verificação de segurança para tableData
                if (!isSpecialTable && (!tableData || typeof tableData !== 'object')) {
                    console.warn('Dados não encontrados ou inválidos para categoria:', cat);
                    return; // Pular esta categoria
                }
                
                const groupDiv = document.createElement('div');
                groupDiv.className = 'table-card cross-group';
                groupDiv.setAttribute('data-category', cat);
                
                let title = '';
                switch(cat) {
                    case 'oferta_quantidade':
                        title = 'Tabela 1 - Ofertas por região';
                        break;
                    case 'venda_quantidade':
                        title = 'Tabela 2 - Vendas por região';
                        break;
                    case 'valor_ponderado_oferta':
                        title = 'Tabela 3 - Oferta Valor Ponderado por região (R$/m²)';
                        break;
                    case 'valor_ponderado_venda':
                        title = 'Tabela 4 - Venda Valor Ponderado por região (R$/m²)';
                        break;
                    case 'oferta_m2':
                        title = 'Tabela 5 - Oferta total por região (em m²)';
                        break;
                    case 'venda_m2':
                        title = 'Tabela 6 - Venda total por região (em m²)';
                        break;
                    case 'gastos_pos_entrega':
                        // Capturar período selecionado para subtítulo dinâmico
                        const filters = getCrossTabsFilters();
                        const periodoSelecionado = filters.periodo || 'Setembro 2025';
                        title = 'Tabela 7 - Gastos Pós-Entrega e Impactos Econômicos por Região';
                        break;
                    case 'gastos_por_categoria':
                        title = 'Tabela 8 - Gastos Pós-entrega por Categoria e Região (R$ Mi)';
                        break;
                }
                
                // Cabeçalho com título e botão PDF (como nas tabelas padrão)
                const headerDiv = document.createElement('div');
                headerDiv.className = 'table-header';
                const h3 = document.createElement('h3');
                h3.className = 'table-title';
                h3.textContent = title;
                headerDiv.appendChild(h3);
                
                // Subtítulo especial para gastos_pos_entrega
                if (cat === 'gastos_pos_entrega') {
                    // Subtítulo removido conforme solicitado
                }
                
                const pdfBtn = document.createElement('button');
                pdfBtn.className = 'filter-btn apply-btn';
                pdfBtn.textContent = '📄 PDF';
                pdfBtn.onclick = function() { exportAllTablesToPDF(); };
                headerDiv.appendChild(pdfBtn);
                
                groupDiv.appendChild(headerDiv);
                
                // Estrutura especial para gastos_pos_entrega
                if (cat === 'gastos_pos_entrega') {
                    // Criar tabela com estrutura especial
                    const table = document.createElement('table');
                    table.className = 'data-table';
                    const thead = document.createElement('thead');
                    
                    // Cabeçalho único para tabela gastos_pos_entrega
                    const headerRow = document.createElement('tr');
                    ['Região', 'VGV (R$/Mi)', 'Padrão', '% Gastos', 'Gastos (R$ Mi)', 'Participação (%)', 'PIB (R$ Mi)', 'Tributos (R$ Mi)', 'Empregos'].forEach(function(headerText, index) {
                        const th = document.createElement('th');
                        
                        // Primeira coluna (Região) sem ordenação, outras com ordenação
                        if (index === 0) {
                            th.textContent = headerText;
                        } else {
                            th.innerHTML = headerText + ' <span style="cursor: pointer; color: #1976D2; font-size: 12px; margin-left: 4px;" onclick="sortGastosTable(this, ' + index + ')" title="Clique para ordenar">⇅</span>';
                        }
                        
                        th.style.textAlign = 'center';
                        th.style.fontWeight = '600';
                        th.style.fontSize = '12px';
                        th.style.padding = '8px 4px';
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table.appendChild(thead);
                    
                    const tbody = document.createElement('tbody');
                    
                    // Calcular dados especiais para cada bairro
                    const bairros = Object.keys(tableData).sort();
                    let totalVGV = 0;
                    let totalGastos = 0;
                    
                    // Classificação por padrão construtivo das regiões
                    const padraoRegioes = {
                        'Alto': ['NOROESTE', 'SUDOESTE', 'JARDIM BOTÂNICO', 'ASA SUL', 'ASA NORTE', 'LAGO NORTE'],
                        'Médio': ['ÁGUAS CLARAS', 'GUARÁ', 'SOBRADINHO', 'SOBRADINHO II', 'PARK SUL', 'TAGUATINGA'],
                        'Popular': ['CEILÂNDIA', 'PLANALTINA', 'SANTA MARIA', 'GAMA', 'RECANTO DAS EMAS', 'SAMAMBAIA']
                    };
                    
                    // Função para determinar padrão da região
                    function getPadraoRegiao(nomeRegiao) {
                        const regiaoUpper = nomeRegiao.toUpperCase();
                        for (const [padrao, regioes] of Object.entries(padraoRegioes)) {
                            if (regioes.some(r => regiaoUpper.includes(r) || r.includes(regiaoUpper))) {
                                return padrao;
                            }
                        }
                        return 'Médio'; // Padrão default
                    }
                    
                    // Função para obter percentual baseado no padrão
                    function getPercentualPadrao(padrao) {
                        switch (padrao) {
                            case 'Alto': return 0.25;
                            case 'Popular': return 0.10;
                            default: return 0.15; // Médio
                        }
                    }
                    
                    // Primeiro, calcular totais para percentuais
                    bairros.forEach(function(bairro) {
                        Object.keys(tableData[bairro] || {}).forEach(function(q) {
                            const gastosPosObra = tableData[bairro][q] || 0;
                            totalGastos += gastosPosObra;
                            
                            // Recalcular VGV baseado nos gastos e padrão da região
                            const padrao = getPadraoRegiao(bairro);
                            const percentual = getPercentualPadrao(padrao);
                            totalVGV += gastosPosObra / percentual;
                        });
                    });
                    
                    bairros.forEach(function(bairro) {
                        const row = document.createElement('tr');
                        
                        // Região
                        const tdRegiao = document.createElement('td');
                        tdRegiao.textContent = bairro;
                        tdRegiao.style.fontWeight = '500';
                        row.appendChild(tdRegiao);
                        
                        // Calcular dados agregados do bairro
                        let bairroVGV = 0;
                        let bairroGastos = 0;
                        
                        // Determinar padrão baseado na região (não no valor)
                        const bairroPadrao = getPadraoRegiao(bairro);
                        const percentualGasto = getPercentualPadrao(bairroPadrao);
                        
                        Object.keys(tableData[bairro] || {}).forEach(function(q) {
                            const gastosPosObra = tableData[bairro][q] || 0;
                            bairroGastos += gastosPosObra;
                            // VGV = gastos / percentual_do_padrao
                            bairroVGV += gastosPosObra / percentualGasto;
                        });
                        
                        // VGV (R$/Mi)
                        const tdVGV = document.createElement('td');
                        const vgvMilhoes = bairroVGV / 1000000;
                        tdVGV.textContent = vgvMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        tdVGV.style.textAlign = 'right';
                        row.appendChild(tdVGV);
                        
                        // Padrão do Imóvel
                        const tdPadrao = document.createElement('td');
                        tdPadrao.textContent = bairroPadrao;
                        tdPadrao.style.textAlign = 'center';
                        row.appendChild(tdPadrao);
                        
                        // % Gastos Pós-entrega
                        const tdPercent = document.createElement('td');
                        tdPercent.textContent = (percentualGasto * 100).toFixed(0) + '%';
                        tdPercent.style.textAlign = 'center';
                        row.appendChild(tdPercent);
                        
                        // Gastos Pós-entrega (R$ milhões)
                        const tdGastos = document.createElement('td');
                        const gastosMilhoes = bairroGastos / 1000000;
                        tdGastos.textContent = gastosMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        tdGastos.style.textAlign = 'right';
                        row.appendChild(tdGastos);
                        
                        // Participação no Total (%)
                        const tdParticipacao = document.createElement('td');
                        const participacao = totalGastos > 0 ? (bairroGastos / totalGastos) * 100 : 0;
                        tdParticipacao.textContent = participacao.toFixed(1) + '%';
                        tdParticipacao.style.textAlign = 'center';
                        row.appendChild(tdParticipacao);
                        
                        // PIB Adicional (R$ milhões) - 0,17 multiplicador MIP
                        const tdPIB = document.createElement('td');
                        const pibAdicional = gastosMilhoes * 0.17;
                        tdPIB.textContent = pibAdicional.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        tdPIB.style.textAlign = 'right';
                        row.appendChild(tdPIB);
                        
                        // Tributos Gerados (R$ milhões) - 0,09 multiplicador MIP
                        const tdTributos = document.createElement('td');
                        const tributos = gastosMilhoes * 0.09;
                        tdTributos.textContent = tributos.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        tdTributos.style.textAlign = 'right';
                        row.appendChild(tdTributos);
                        
                        // Empregos Gerados (unidades) - 16,85 por R$ 1 mi MIP
                        const tdEmpregos = document.createElement('td');
                        const empregos = gastosMilhoes * 16.85;
                        tdEmpregos.textContent = Math.round(empregos).toLocaleString('pt-BR');
                        tdEmpregos.style.textAlign = 'right';
                        row.appendChild(tdEmpregos);
                        
                        tbody.appendChild(row);
                    });
                    
                    // Linha totalizadora
                    const totalRow = document.createElement('tr');
                    totalRow.style.fontWeight = '600';
                    totalRow.style.backgroundColor = '#f8f9fa';
                    totalRow.style.borderTop = '2px solid #007bff';
                    
                    // Calcular totais
                    let totalVGVFinal = 0;
                    let totalGastosFinal = 0;
                    let totalPIBFinal = 0;
                    let totalTributosFinal = 0;
                    let totalEmpregosFinal = 0;
                    
                    bairros.forEach(function(bairro) {
                        let bairroGastos = 0;
                        const padraoRegiao = getPadraoRegiao(bairro);
                        const percentualGasto = getPercentualPadrao(padraoRegiao);
                        
                        Object.keys(tableData[bairro] || {}).forEach(function(q) {
                            const gastosPosObra = tableData[bairro][q] || 0;
                            bairroGastos += gastosPosObra;
                        });
                        
                        const bairroVGV = bairroGastos / percentualGasto;
                        const gastosMilhoes = bairroGastos / 1000000;
                        
                        totalVGVFinal += bairroVGV;
                        totalGastosFinal += bairroGastos;
                        totalPIBFinal += gastosMilhoes * 0.17;
                        totalTributosFinal += gastosMilhoes * 0.09;
                        totalEmpregosFinal += gastosMilhoes * 16.85;
                    });
                    
                    // Células do total
                    const cells = [
                        'TOTAL GERAL',
                        (totalVGVFinal / 1000000).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}),
                        '-',
                        '-',
                        (totalGastosFinal / 1000000).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}),
                        '100,0%',
                        totalPIBFinal.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}),
                        totalTributosFinal.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}),
                        Math.round(totalEmpregosFinal).toLocaleString('pt-BR')
                    ];
                    
                    cells.forEach(function(cellText, index) {
                        const td = document.createElement('td');
                        td.textContent = cellText;
                        if (index === 0) {
                            td.style.textAlign = 'left';
                            td.style.fontWeight = '700';
                        } else if (index === 2 || index === 3 || index === 5) {
                            td.style.textAlign = 'center';
                        } else {
                            td.style.textAlign = 'right';
                        }
                        totalRow.appendChild(td);
                    });
                    
                    tbody.appendChild(totalRow);
                    
                    table.appendChild(tbody);
                    groupDiv.appendChild(table);
                } else if (cat === 'gastos_por_categoria') {
                    // Estrutura especial para gastos_por_categoria (Tabela 8)
                    // CORREÇÃO FINAL: Aplicar percentuais das categorias diretamente no VGV base
                    // mas usando exatamente o mesmo VGV que gera os gastos da Tabela 7
                    const table = document.createElement('table');
                    table.className = 'data-table';
                    const thead = document.createElement('thead');
                    
                    // Definir categorias e seus percentuais por padrão (da pesquisa)
                    // PERCENTUAIS AJUSTADOS para soma exata de 25%, 15% e 10%
                    const categorias = [
                        { nome: 'Obras Habitações', alto: 0.043, medio: 0.030, popular: 0.035 },
                        { nome: 'Cama Mesa Banho', alto: 0.013, medio: 0.006, popular: 0.003 },
                        { nome: 'Artigos Decoração', alto: 0.030, medio: 0.023, popular: 0.008 },
                        { nome: 'Móveis Planejados', alto: 0.030, medio: 0.015, popular: 0.007 },
                        { nome: 'Eletroeletrônicos', alto: 0.018, medio: 0.015, popular: 0.004 },
                        { nome: 'Instalações Elétricas', alto: 0.019, medio: 0.011, popular: 0.016 },
                        { nome: 'Mobiliário', alto: 0.063, medio: 0.030, popular: 0.022 },
                        { nome: 'Outros Serviços', alto: 0.034, medio: 0.020, popular: 0.005 }
                    ];
                    
                    // Primeira linha: Título
                    const titleRow = document.createElement('tr');
                    const thRegion = document.createElement('th');
                    thRegion.textContent = 'Região';
                    thRegion.style.textAlign = 'left';
                    thRegion.style.minWidth = '120px';
                    titleRow.appendChild(thRegion);
                    
                    // Cabeçalhos das categorias
                    categorias.forEach(function(categoria, index) {
                        const th = document.createElement('th');
                        th.innerHTML = categoria.nome + ' <span style="cursor: pointer; color: #1976D2; font-size: 12px; margin-left: 4px;" onclick="sortCategoriaValoresTable(this, ' + (index + 1) + ')" title="Clique para ordenar">⇅</span>';
                        th.style.textAlign = 'center';
                        th.style.fontWeight = '600';
                        th.style.fontSize = '11px';
                        th.style.padding = '8px 4px';
                        th.style.minWidth = '90px';
                        titleRow.appendChild(th);
                    });
                    
                    // Coluna Total
                    const thTotal = document.createElement('th');
                    thTotal.innerHTML = 'Total <span style="cursor: pointer; color: #1976D2; font-size: 12px; margin-left: 4px;" onclick="sortCategoriaValoresTable(this, ' + (categorias.length + 1) + ')" title="Clique para ordenar">⇅</span>';
                    thTotal.style.textAlign = 'center';
                    thTotal.style.fontWeight = '600';
                    thTotal.style.fontSize = '11px';
                    thTotal.style.padding = '8px 4px';
                    titleRow.appendChild(thTotal);
                    
                    thead.appendChild(titleRow);
                    table.appendChild(thead);
                    
                    const tbody = document.createElement('tbody');
                    
                    // CORREÇÃO CRÍTICA: Reconstruir o VGV que gerou os gastos da Tabela 7
                    // Usar os gastos da Tabela 7 para reverter ao VGV original
                    const gastosData = cross.gastos_pos_entrega || {};
                    
                    // Classificação de regiões por padrão
                    const padraoRegioes = {
                        'Alto': ['NOROESTE', 'SUDOESTE', 'JARDIM BOTÂNICO', 'ASA SUL', 'ASA NORTE', 'LAGO NORTE'],
                        'Médio': ['ÁGUAS CLARAS', 'GUARÁ', 'SOBRADINHO', 'SOBRADINHO II', 'PARK SUL', 'TAGUATINGA'],
                        'Popular': ['CEILÂNDIA', 'PLANALTINA', 'SANTA MARIA', 'GAMA', 'RECANTO DAS EMAS', 'SAMAMBAIA']
                    };
                    
                    function getPadraoRegiao(nomeRegiao) {
                        const regiaoUpper = nomeRegiao.toUpperCase();
                        for (const [padrao, regioes] of Object.entries(padraoRegioes)) {
                            if (regioes.some(r => regiaoUpper.includes(r) || r.includes(regiaoUpper))) {
                                return padrao;
                            }
                        }
                        return 'Médio'; // Padrão default
                    }
                    
                    // Calcular total da Tabela 7 para verificação
                    let totalGastosTabela7 = 0;
                    Object.keys(gastosData).forEach(function(regiao) {
                        Object.values(gastosData[regiao] || {}).forEach(function(valor) {
                            totalGastosTabela7 += valor || 0;
                        });
                    });
                    
                    console.log('Tabela 8 - LÓGICA CORRETA: Total da Tabela 7 =', (totalGastosTabela7 / 1000000).toFixed(2), 'milhões');
                    
                    // VERIFICAÇÃO: Confirmar somas dos percentuais
                    let somaAlto = 0, somaMedio = 0, somaPopular = 0;
                    categorias.forEach(function(cat) {
                        somaAlto += cat.alto;
                        somaMedio += cat.medio;
                        somaPopular += cat.popular;
                    });
                    console.log('Verificação percentuais - Alto:', (somaAlto * 100).toFixed(1) + '%', 'Médio:', (somaMedio * 100).toFixed(1) + '%', 'Popular:', (somaPopular * 100).toFixed(1) + '%');
                    
                    if (Math.abs(somaAlto - 0.25) < 0.001 && Math.abs(somaMedio - 0.15) < 0.001 && Math.abs(somaPopular - 0.10) < 0.001) {
                        console.log('✅ PERCENTUAIS CORRETOS: Somas exatas de 25%, 15% e 10%');
                    } else {
                        console.log('❌ PERCENTUAIS INCORRETOS: Necessário ajuste');
                    }
                    
                    // ABORDAGEM CORRETA: Reconstruir VGV a partir dos gastos da Tabela 7
                    const vgvReconstruidoPorRegiao = {};
                    
                    Object.keys(gastosData).forEach(function(regiao) {
                        // Somar gastos da região na Tabela 7
                        let gastosRegiao = 0;
                        Object.values(gastosData[regiao] || {}).forEach(function(valor) {
                            gastosRegiao += valor || 0;
                        });
                        
                        // Determinar padrão para reverter ao VGV
                        const padraoRegiao = getPadraoRegiao(regiao);
                        let percentualCBIC = 0.15; // Médio
                        if (padraoRegiao === 'Alto') percentualCBIC = 0.25;
                        else if (padraoRegiao === 'Popular') percentualCBIC = 0.10;
                        
                        // VGV = gastos / percentual
                        vgvReconstruidoPorRegiao[regiao] = gastosRegiao / percentualCBIC;
                    });
                    
                    console.log('Tabela 8 - VGV reconstruído (primeiras 3 regiões):');
                    
                    // Calcular totais por categoria para todo o DF
                    const totaisPorCategoria = categorias.map(() => 0);
                    let totalGeral = 0;
                    
                    // Processar cada região
                    const regioes = Object.keys(vgvReconstruidoPorRegiao).sort();
                    
                    regioes.forEach(function(regiao, index) {
                        const row = document.createElement('tr');
                        
                        // Coluna Região
                        const tdRegiao = document.createElement('td');
                        tdRegiao.textContent = regiao;
                        tdRegiao.style.fontWeight = '500';
                        tdRegiao.style.textAlign = 'left';
                        tdRegiao.style.paddingLeft = '8px';
                        row.appendChild(tdRegiao);
                        
                        // VGV reconstruído da região
                        const vgvRegiao = vgvReconstruidoPorRegiao[regiao] || 0;
                        
                        // Determinar padrão da região
                        const padraoRegiao = getPadraoRegiao(regiao);
                        
                        // Verificação: gastos da Tabela 7
                        let gastosOriginaisTabela7 = 0;
                        Object.values(gastosData[regiao] || {}).forEach(function(valor) {
                            gastosOriginaisTabela7 += valor || 0;
                        });
                        
                        let totalLinhaRegiao = 0;
                        
                        // LÓGICA CORRETA: Aplicar percentuais das categorias diretamente no VGV
                        categorias.forEach(function(categoria, catIndex) {
                            const td = document.createElement('td');
                            
                            // Obter percentual da categoria baseado no padrão da região
                            let percentualCategoria = categoria.medio; // default
                            if (padraoRegiao === 'Alto') {
                                percentualCategoria = categoria.alto;
                            } else if (padraoRegiao === 'Popular') {
                                percentualCategoria = categoria.popular;
                            }
                            
                            // APLICAR PERCENTUAL DIRETAMENTE NO VGV
                            const valorCategoria = vgvRegiao * percentualCategoria;
                            totalLinhaRegiao += valorCategoria;
                            totaisPorCategoria[catIndex] += valorCategoria;
                            
                            // CORREÇÃO: Formatar valor em MILHÕES (mesmo padrão da Tabela 7)
                            const valorMilhoes = valorCategoria / 1000000;
                            td.textContent = valorMilhoes.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                            
                            td.style.textAlign = 'right';
                            td.style.padding = '6px 8px';
                            td.style.fontSize = '11px';
                            row.appendChild(td);
                        });
                        
                        totalGeral += totalLinhaRegiao;
                        
                        // Log para verificação (primeiras 3 regiões)
                        if (index < 3) {
                            console.log(`${regiao}: VGV=${(vgvRegiao/1000000).toFixed(2)}M, Gastos Originais=${(gastosOriginaisTabela7/1000000).toFixed(2)}M, Categorias Calculadas=${(totalLinhaRegiao/1000000).toFixed(2)}M, Padrão=${padraoRegiao}`);
                        }
                        
                        // CORREÇÃO: Coluna Total da linha em MILHÕES
                        const tdTotal = document.createElement('td');
                        const totalMilhoes = totalLinhaRegiao / 1000000;
                        tdTotal.textContent = totalMilhoes.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                        tdTotal.style.textAlign = 'right';
                        tdTotal.style.padding = '6px 8px';
                        tdTotal.style.fontSize = '11px';
                        tdTotal.style.fontWeight = '500';
                        row.appendChild(tdTotal);
                        
                        tbody.appendChild(row);
                    });
                    
                    // Linha totalizadora
                    const totalRow = document.createElement('tr');
                    totalRow.style.fontWeight = '600';
                    totalRow.style.backgroundColor = '#f8f9fa';
                    totalRow.style.borderTop = '2px solid #007bff';
                    
                    // Célula "TOTAL"
                    const tdTotalLabel = document.createElement('td');
                    tdTotalLabel.textContent = 'TOTAL';
                    tdTotalLabel.style.textAlign = 'left';
                    tdTotalLabel.style.fontWeight = '700';
                    tdTotalLabel.style.paddingLeft = '8px';
                    totalRow.appendChild(tdTotalLabel);
                    
                    // Totais por categoria
                    totaisPorCategoria.forEach(function(total) {
                        const td = document.createElement('td');
                        const totalMilhoes = total / 1000000;
                        td.textContent = totalMilhoes.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                        td.style.textAlign = 'right';
                        td.style.fontWeight = '700';
                        td.style.padding = '6px 8px';
                        totalRow.appendChild(td);
                    });
                    
                    // Total geral
                    const tdTotalGeral = document.createElement('td');
                    const totalGeralMilhoes = totalGeral / 1000000;
                    tdTotalGeral.textContent = totalGeralMilhoes.toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                    tdTotalGeral.style.textAlign = 'right';
                    tdTotalGeral.style.fontWeight = '700';
                    tdTotalGeral.style.padding = '6px 8px';
                    totalRow.appendChild(tdTotalGeral);
                    
                    tbody.appendChild(totalRow);
                    table.appendChild(tbody);
                    groupDiv.appendChild(table);
                    
                    // Logs finais de verificação
                    console.log('VERIFICAÇÃO FINAL - LÓGICA CORRETA:');
                    console.log('Tabela 7 - Gastos totais:', (totalGastosTabela7 / 1000000).toFixed(2), 'milhões');
                    console.log('Tabela 8 - Categorias calculadas:', (totalGeral / 1000000).toFixed(2), 'milhões');
                    console.log('Diferença:', ((Math.abs(totalGeral - totalGastosTabela7)) / 1000000).toFixed(2), 'milhões');
                    
                    const diferencaPercentual = Math.abs((totalGeral - totalGastosTabela7) / totalGastosTabela7) * 100;
                    console.log('Diferença percentual:', diferencaPercentual.toFixed(2), '%');
                    
                    if (diferencaPercentual < 0.1) {
                        console.log('✅ SUCESSO: Lógica correta - VGV × % categorias = Gastos Tabela 7');
                    } else {
                        console.log('❌ Ainda há divergência na lógica');
                    }
                    
                    // Adicionar nota explicativa com padrão exato da aba insights
                    const noteDiv = document.createElement('div');
                    noteDiv.style.marginTop = '15px';
                    noteDiv.style.fontSize = '13px';
                    noteDiv.style.color = '#555';
                    noteDiv.style.padding = '12px';
                    noteDiv.style.backgroundColor = '#f8f9fa';
                    noteDiv.style.borderLeft = '3px solid #4A90E2';
                    noteDiv.style.borderRadius = '4px';
                    noteDiv.style.lineHeight = '1.6';
                    noteDiv.innerHTML = '<strong>📊 Metodologia:</strong> Percentuais de gastos por categoria aplicados sobre o VGV.<br>' +
                        '<strong>Fonte:</strong> <a href="https://cbic.org.br/wp-content/uploads/2021/02/pos-obraestudo-cbic.pdf" target="_blank" style="color:#4A90E2;text-decoration:none;">Estudo CBIC 2021 - Pós-obra: geração de renda e emprego</a>';
                    groupDiv.appendChild(noteDiv);
                } else {

                    // Estrutura normal para outras tabelas
                    const table = document.createElement('table');
                table.className = 'data-table';
                const thead = document.createElement('thead');
                
                // Primeira linha: Título sobre as colunas de quartos
                const titleRow = document.createElement('tr');
                const thRegion = document.createElement('th');
                thRegion.textContent = '';
                titleRow.appendChild(thRegion);
                
                const roomSet = new Set();
                if (tableData && typeof tableData === 'object') {
                    Object.values(tableData).forEach(function(obj) {
                        if (obj && typeof obj === 'object') {
                            Object.keys(obj).forEach(function(q) { roomSet.add(q); });
                        }
                    });
                }
                let rooms = Array.from(roomSet);
                rooms = rooms.filter(r => r !== '');
                rooms.sort(function(a,b) {
                    const order = {'1':1,'2':2,'3':3,'4+':4};
                    return (order[a] || 5) - (order[b] || 5);
                });
                
                const thQuartos = document.createElement('th');
                thQuartos.textContent = 'Número de Quartos';
                thQuartos.setAttribute('colspan', rooms.length);
                thQuartos.style.textAlign = 'center';
                thQuartos.style.fontWeight = '600';
                thQuartos.style.borderBottom = '1px solid #ddd';
                titleRow.appendChild(thQuartos);
                
                const thTotalTitle = document.createElement('th');
                thTotalTitle.textContent = 'Total';
                thTotalTitle.style.textAlign = 'center';
                thTotalTitle.style.fontWeight = '600';
                thTotalTitle.style.borderBottom = '1px solid #ddd';
                titleRow.appendChild(thTotalTitle);
                
                thead.appendChild(titleRow);
                
                // Segunda linha: Cabeçalhos das colunas
                const hRow = document.createElement('tr');
                const thEmpty = document.createElement('th');
                thEmpty.textContent = 'Região';
                thEmpty.style.borderTop = 'none';
                hRow.appendChild(thEmpty);
                
                rooms.forEach(function(q) {
                    const th = document.createElement('th');
                    th.textContent = q;
                    th.style.borderTop = 'none';
                    hRow.appendChild(th);
                });
                
                const thTotal = document.createElement('th');
                thTotal.innerHTML = '<span style="cursor: pointer; color: #1976D2; font-size: 12px;" onclick="sortCrossTable(this, \'' + cat + '\')" title="Clique para ordenar">⇅</span>';
                thTotal.style.borderTop = 'none';
                hRow.appendChild(thTotal);
                thead.appendChild(hRow);
                table.appendChild(thead);
                const tbody = document.createElement('tbody');
                const bairros = Object.keys(tableData).sort();
                
                // Calcular valores para barras gráficas e setas
                const allValues = [];
                const rowTotals = {};
                
                bairros.forEach(function(bairro) {
                    let rowTotalValor = 0;
                    let rowTotalArea = 0;
                    
                    rooms.forEach(function(q) {
                        const val = (tableData[bairro] && tableData[bairro][q]) ? tableData[bairro][q] : 0;
                        if (val > 0) allValues.push(val);
                        
                        if (cat.includes('valor_ponderado')) {
                            const rawDataKey = cat === 'valor_ponderado_oferta' ? '_rawOferta' : '_rawVenda';
                            const rawData = cross[rawDataKey];
                            if (rawData && rawData[bairro] && rawData[bairro][q]) {
                                rowTotalValor += rawData[bairro][q].totalValor;
                                rowTotalArea += rawData[bairro][q].totalArea;
                            }
                        }
                    });
                    
                    if (cat.includes('valor_ponderado')) {
                        rowTotals[bairro] = rowTotalArea > 0 ? (rowTotalValor / rowTotalArea) : 0;
                    } else {
                        let rowSum = 0;
                        rooms.forEach(function(q) {
                            rowSum += (tableData[bairro] && tableData[bairro][q]) ? tableData[bairro][q] : 0;
                        });
                        rowTotals[bairro] = rowSum;
                    }
                    
                    if (rowTotals[bairro] > 0) allValues.push(rowTotals[bairro]);
                });
                
                const seriesMin = allValues.length > 0 ? Math.min(...allValues) : 0;
                const seriesMax = allValues.length > 0 ? Math.max(...allValues) : 0;
                
                function getBarWidth(value) {
                    if (seriesMax === seriesMin) return 50;
                    return ((value - seriesMin) / (seriesMax - seriesMin)) * 100;
                }
                
                bairros.forEach(function(bairro) {
                    const row = document.createElement('tr');
                    const tdB = document.createElement('td');
                    tdB.textContent = bairro;
                    tdB.style.textAlign = 'left';
                    tdB.style.fontWeight = '500';
                    row.appendChild(tdB);
                    
                    // Para valores ponderados, precisamos agregar os dados brutos
                    let rowTotalValor = 0;
                    let rowTotalArea = 0;
                    
                    rooms.forEach(function(q) {
                        const val = (tableData[bairro] && tableData[bairro][q]) ? tableData[bairro][q] : 0;
                        const td = document.createElement('td');
                        
                        let displayVal;
                        if (cat.includes('valor_ponderado')) {
                            displayVal = val.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                            
                            // Agregar dados brutos para total correto
                            const rawDataKey = cat === 'valor_ponderado_oferta' ? '_rawOferta' : '_rawVenda';
                            const rawData = cross[rawDataKey];
                            if (rawData && rawData[bairro] && rawData[bairro][q]) {
                                rowTotalValor += rawData[bairro][q].totalValor;
                                rowTotalArea += rawData[bairro][q].totalArea;
                            }
                        } else if (cat === 'gastos_pos_entrega') {
                            // Converter para milhões e formatar
                            const valMilhoes = val / 1000000;
                            displayVal = valMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        } else {
                            displayVal = val.toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                        }
                        
                        // Adicionar setas para maior e menor valor da linha
                        let indicator = '';
                        const rowValues = rooms.map(function(r) {
                            return (tableData[bairro] && tableData[bairro][r]) ? tableData[bairro][r] : 0;
                        }).filter(v => v > 0);
                        
                        if (rowValues.length > 1) {
                            const rowMax = Math.max(...rowValues);
                            const rowMin = Math.min(...rowValues);
                            if (val === rowMax && val > 0) {
                                indicator = ' <span style="color: #555;">▲</span>';
                            } else if (val === rowMin && val > 0) {
                                indicator = ' <span style="color: #555;">▼</span>';
                            }
                        }
                        
                        // Células de quartos sem barras gráficas, apenas texto
                        td.textContent = displayVal + (indicator ? '' : '');
                        if (indicator) {
                            td.innerHTML = displayVal + indicator;
                        }
                        
                        row.appendChild(td);
                    });
                    
                    const tdTotal = document.createElement('td');
                    let displayTotal;
                    const totalValue = rowTotals[bairro];
                    
                    if (cat.includes('valor_ponderado')) {
                        // Total correto: valor ponderado baseado nos dados agregados
                        displayTotal = totalValue.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    } else if (cat === 'gastos_pos_entrega') {
                        // Para gastos pós-entrega, converter para milhões
                        const totalMilhoes = totalValue / 1000000;
                        displayTotal = totalMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    } else {
                        // Para m², somar os valores
                        displayTotal = totalValue.toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                    }
                    
                    // Seta para o total se for maior/menor valor total
                    const allTotals = Object.values(rowTotals).filter(v => v > 0);
                    let totalIndicator = '';
                    if (allTotals.length > 1) {
                        const totalMax = Math.max(...allTotals);
                        const totalMin = Math.min(...allTotals);
                        if (totalValue === totalMax && totalValue > 0) {
                            totalIndicator = ' <span style="color: #555;">▲</span>';
                        } else if (totalValue === totalMin && totalValue > 0) {
                            totalIndicator = ' <span style="color: #555;">▼</span>';
                        }
                    }
                    
                    if (totalValue > 0) {
                        const barWidth = getBarWidth(totalValue);
                        tdTotal.innerHTML = '<div style="position: relative; padding: 4px 8px; border-radius: 4px;">' +
                            '<div style="position: absolute; left: 0; top: 0; bottom: 0; width: ' + barWidth.toFixed(2) + '%; ' +
                            'background: linear-gradient(90deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.25) 100%); ' +
                            'border-radius: 4px; z-index: 0;"></div>' +
                            '<div style="position: relative; z-index: 1;">' + displayTotal + totalIndicator + '</div>' +
                            '</div>';
                    } else {
                        tdTotal.textContent = displayTotal;
                    }
                    
                    row.appendChild(tdTotal);
                    tbody.appendChild(row);
                });
                
                const totalRow = document.createElement('tr');
                const tdLabel = document.createElement('td');
                tdLabel.textContent = 'Total Geral';
                tdLabel.style.fontWeight = '600';
                totalRow.appendChild(tdLabel);
                
                rooms.forEach(function(q) {
                    const td = document.createElement('td');
                    if (cat.includes('valor_ponderado')) {
                        // Total por coluna: agregar dados brutos de todos os bairros
                        let colTotalValor = 0;
                        let colTotalArea = 0;
                        const rawDataKey = cat === 'valor_ponderado_oferta' ? '_rawOferta' : '_rawVenda';
                        const rawData = cross[rawDataKey];
                        
                        bairros.forEach(function(b) {
                            if (rawData && rawData[b] && rawData[b][q]) {
                                colTotalValor += rawData[b][q].totalValor;
                                colTotalArea += rawData[b][q].totalArea;
                            }
                        });
                        
                        const colPonderado = colTotalArea > 0 ? (colTotalValor / colTotalArea) : 0;
                        td.textContent = colPonderado.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    } else if (cat === 'gastos_pos_entrega') {
                        // Para gastos pós-entrega, somar os valores e converter para milhões
                        let sum = 0;
                        bairros.forEach(function(b) {
                            sum += (tableData[b][q] || 0);
                        });
                        const sumMilhoes = sum / 1000000;
                        td.textContent = sumMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    } else {
                        // Para m², somar os valores
                        let sum = 0;
                        bairros.forEach(function(b) {
                            sum += (tableData[b][q] || 0);
                        });
                        td.textContent = sum.toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                    }
                    totalRow.appendChild(td);
                });
                
                // Total geral
                const tdGrand = document.createElement('td');
                if (cat.includes('valor_ponderado')) {
                    // Total geral: agregar todos os dados brutos
                    let grandTotalValor = 0;
                    let grandTotalArea = 0;
                    const rawDataKey = cat === 'valor_ponderado_oferta' ? '_rawOferta' : '_rawVenda';
                    const rawData = cross[rawDataKey];
                    
                    bairros.forEach(function(b) {
                        rooms.forEach(function(q) {
                            if (rawData && rawData[b] && rawData[b][q]) {
                                grandTotalValor += rawData[b][q].totalValor;
                                grandTotalArea += rawData[b][q].totalArea;
                            }
                        });
                    });
                    
                    const grandPonderado = grandTotalArea > 0 ? (grandTotalValor / grandTotalArea) : 0;
                    tdGrand.textContent = grandPonderado.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                } else if (cat === 'gastos_pos_entrega') {
                    // Para gastos pós-entrega, somar todos os valores e converter para milhões
                    let grand = 0;
                    bairros.forEach(function(b) {
                        rooms.forEach(function(q) {
                            grand += (tableData[b][q] || 0);
                        });
                    });
                    const grandMilhoes = grand / 1000000;
                    tdGrand.textContent = grandMilhoes.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                } else {
                    // Para m², somar todos os valores
                    let grand = 0;
                    bairros.forEach(function(b) {
                        rooms.forEach(function(q) {
                            grand += (tableData[b][q] || 0);
                        });
                    });
                    tdGrand.textContent = grand.toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                }
                totalRow.appendChild(tdGrand);
                tbody.appendChild(totalRow);
                table.appendChild(tbody);
                groupDiv.appendChild(table);
                } // Fechamento do bloco else
                
                // Rodapé unificado para gastos_pos_entrega
                if (cat === 'gastos_pos_entrega') {
                    const unifiedFooterDiv = document.createElement('div');
                    unifiedFooterDiv.style.fontSize = '13px';
                    unifiedFooterDiv.style.color = '#555';
                    unifiedFooterDiv.style.marginTop = '15px';
                    unifiedFooterDiv.style.padding = '12px';
                    unifiedFooterDiv.style.backgroundColor = '#f8f9fa';
                    unifiedFooterDiv.style.borderLeft = '3px solid #4A90E2';
                    unifiedFooterDiv.style.borderRadius = '4px';
                    unifiedFooterDiv.style.lineHeight = '1.6';
                    
                    unifiedFooterDiv.innerHTML = `
                        <div style="margin-bottom: 15px; font-weight: 600; color: #343a40; font-size: 13px;">
                            📊 Metodologia e Intepretação dos Dados
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <div style="font-weight: 600; color: #495057; margin-bottom: 6px;">METODOLOGIA</div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Gastos pós-entrega:</strong> Classificação por padrão construtivo - Alto (25% VGV), Médio (15% VGV), Popular (10% VGV)
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Regiões:</strong> Alto: Noroeste, Sudoeste, Jardim Botânico, Asa Sul, Asa Norte, Lago Norte | 
                                Médio: Águas Claras, Guará, Sobradinho, Sobradinho II, Park Sul, Taguatinga | 
                                Popular: Ceilândia, Planaltina, Santa Maria, Gama, Recanto das Emas, Samambaia
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Multiplicadores MIP (IBGE/2020):</strong> PIB (0,17), Tributos (0,09), Empregos (16,85 por R$ 1 milhão)
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Horizonte temporal:</strong> 3 anos pós-entrega
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 12px;">
                            <div style="font-weight: 600; color: #495057; margin-bottom: 6px;">INTERPRETAÇÃO DAS COLUNAS</div>
                            <div style="margin-bottom: 2px;">
                                <strong>• VGV:</strong> Volume financeiro total de vendas imobiliárias por região
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Gastos:</strong> Recursos financeiros movimentados pelos novos moradores (% do VGV conforme padrão regional)
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Participação:</strong> Representatividade regional no total de gastos do DF
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• PIB:</strong> Contribuição estimada para o produto interno bruto local
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Tributos:</strong> Receita tributária gerada (impostos diretos e indiretos)
                            </div>
                            <div style="margin-bottom: 2px;">
                                <strong>• Empregos:</strong> Postos de trabalho diretos e indiretos gerados
                            </div>
                        </div>
                        
                        <div style="margin-top: 15px; font-size: 12px; color: #777; border-top: 1px solid #dee2e6; padding-top: 8px;">
                            <strong>Fonte:</strong> <a href="https://cbic.org.br/wp-content/uploads/2021/02/pos-obraestudo-cbic.pdf" 
                                                      target="_blank" style="color:#4A90E2;text-decoration:none;">
                                Estudo CBIC 2021 - Pós-obra: geração de renda e emprego
                            </a>
                        </div>
                    `;
                    
                    groupDiv.appendChild(unifiedFooterDiv);
                }
                
                container.appendChild(groupDiv);
            });
        }

        // Função para ordenar tabelas crosstabs
        function sortCrossTable(element, category) {
            const table = element.closest('table');
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            
            // Excluir a linha "Total Geral"
            const dataRows = rows.filter(row => row.cells[0].textContent !== 'Total Geral');
            const totalRow = rows.find(row => row.cells[0].textContent === 'Total Geral');
            
            // Verificar direção atual da ordenação
            const isAscending = element.getAttribute('data-sort') !== 'desc';
            element.setAttribute('data-sort', isAscending ? 'desc' : 'asc');
            
            // Atualizar ícone
            element.innerHTML = '<span style="cursor: pointer; color: #1976D2; font-size: 12px;" onclick="sortCrossTable(this, \'' + category + '\')" title="Clique para ordenar">' + 
                (isAscending ? '↓' : '↑') + '</span>';
            
            // Índice da coluna Total (última coluna)
            const totalColumnIndex = dataRows[0].cells.length - 1;
            
            // Função para converter texto brasileiro para número
            function parseValueBR(text) {
                if (!text || text.trim() === '') return 0;
                
                // Remover setas e espaços extras
                let cleanText = text.replace(/[▲▼↑↓]/g, '').trim();
                
                // Se contém vírgula E ponto, é formato brasileiro (123.456,78)
                if (cleanText.includes('.') && cleanText.includes(',')) {
                    // Remover pontos (separadores de milhares) e trocar vírgula por ponto
                    cleanText = cleanText.replace(/\./g, '').replace(',', '.');
                }
                // Se contém apenas vírgula, é decimal brasileiro
                else if (cleanText.includes(',') && !cleanText.includes('.')) {
                    cleanText = cleanText.replace(',', '.');
                }
                // Se contém apenas pontos, verificar se é separador de milhares ou decimal
                else if (cleanText.includes('.')) {
                    const parts = cleanText.split('.');
                    if (parts.length === 2 && parts[1].length <= 2) {
                        // É decimal (ex: 123.45)
                        // Não fazer nada
                    } else {
                        // São separadores de milhares (ex: 123.456)
                        cleanText = cleanText.replace(/\./g, '');
                    }
                }
                
                const value = parseFloat(cleanText) || 0;
                console.log('Parsing:', text, '->', cleanText, '->', value);
                return value;
            }
            
            // Ordenar por valor da coluna Total
            dataRows.sort(function(a, b) {
                const aText = a.cells[totalColumnIndex].textContent || a.cells[totalColumnIndex].innerText;
                const bText = b.cells[totalColumnIndex].textContent || b.cells[totalColumnIndex].innerText;
                
                const aValue = parseValueBR(aText);
                const bValue = parseValueBR(bText);
                
                return isAscending ? bValue - aValue : aValue - bValue;
            });
            
            // Limpar tbody e adicionar linhas ordenadas
            tbody.innerHTML = '';
            dataRows.forEach(row => tbody.appendChild(row));
            if (totalRow) tbody.appendChild(totalRow);
        }

        // Função para ordenar tabela de gastos pós-entrega (Tabela 7)
        function sortGastosTable(element, columnIndex) {
            const table = element.closest('table');
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            
            // Excluir a linha "TOTAL GERAL"
            const dataRows = rows.filter(row => row.cells[0].textContent !== 'TOTAL GERAL');
            const totalRow = rows.find(row => row.cells[0].textContent === 'TOTAL GERAL');
            
            // Verificar direção atual da ordenação
            const currentSort = element.getAttribute('data-sort') || 'none';
            const isAscending = currentSort !== 'asc';
            
            // Atualizar ícone e preservar data-sort no novo elemento
            const parentTh = element.parentElement;
            const headerText = parentTh.textContent.replace(/[⇅↑↓]/g, '').trim();
            parentTh.innerHTML = headerText + ' <span style="cursor: pointer; color: #1976D2; font-size: 12px; margin-left: 4px;" onclick="sortGastosTable(this, ' + columnIndex + ')" title="Clique para ordenar" data-sort="' + (isAscending ? 'asc' : 'desc') + '">' + 
                (isAscending ? '↑' : '↓') + '</span>';
            
            // Função para converter texto brasileiro para número
            function parseValueBR(text) {
                if (!text || text.trim() === '' || text.trim() === '-') return 0;
                
                // Remover setas, espaços extras e símbolos
                let cleanText = text.replace(/[▲▼↑↓%]/g, '').trim();
                
                // Se contém vírgula E ponto, é formato brasileiro (123.456,78)
                if (cleanText.includes('.') && cleanText.includes(',')) {
                    // Remover pontos (separadores de milhares) e trocar vírgula por ponto
                    cleanText = cleanText.replace(/\./g, '').replace(',', '.');
                }
                // Se contém apenas vírgula, é decimal brasileiro
                else if (cleanText.includes(',') && !cleanText.includes('.')) {
                    cleanText = cleanText.replace(',', '.');
                }
                // Se contém apenas pontos, verificar se é separador de milhares ou decimal
                else if (cleanText.includes('.')) {
                    const parts = cleanText.split('.');
                    if (parts.length === 2 && parts[1].length <= 2) {
                        // É decimal (ex: 123.45)
                        // Não fazer nada
                    } else {
                        // São separadores de milhares (ex: 123.456)
                        cleanText = cleanText.replace(/\./g, '');
                    }
                }
                
                const value = parseFloat(cleanText) || 0;
                return value;
            }
            
            // Função para ordenação alfabética (para coluna Padrão)
            function compareText(a, b) {
                const textA = (a || '').toString().toLowerCase();
                const textB = (b || '').toString().toLowerCase();
                if (textA < textB) return -1;
                if (textA > textB) return 1;
                return 0;
            }
            
            // Ordenar baseado no tipo de coluna
            dataRows.sort(function(a, b) {
                const aText = a.cells[columnIndex].textContent || a.cells[columnIndex].innerText;
                const bText = b.cells[columnIndex].textContent || b.cells[columnIndex].innerText;
                
                // Para coluna Padrão (índice 2), usar ordenação alfabética
                if (columnIndex === 2) {
                    const comparison = compareText(aText, bText);
                    return isAscending ? comparison : -comparison;
                } else {
                    // Para colunas numéricas, usar parseValueBR
                    const aValue = parseValueBR(aText);
                    const bValue = parseValueBR(bText);
                    return isAscending ? aValue - bValue : bValue - aValue;
                }
            });
            
            // Limpar tbody e adicionar linhas ordenadas
            tbody.innerHTML = '';
            dataRows.forEach(row => tbody.appendChild(row));
            if (totalRow) tbody.appendChild(totalRow);
        }

        // Função para ordenar tabela de gastos por categoria com valores em milhões (Tabela 8)
        function sortCategoriaValoresTable(element, columnIndex) {
            const table = element.closest('table');
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            
            // Excluir a linha "TOTAL"
            const dataRows = rows.filter(row => row.cells[0].textContent !== 'TOTAL');
            const totalRow = rows.find(row => row.cells[0].textContent === 'TOTAL');
            
            // Verificar direção atual da ordenação
            const currentSort = element.getAttribute('data-sort') || 'none';
            const isAscending = currentSort !== 'asc';
            
            // Atualizar ícone e preservar data-sort no novo elemento
            const parentTh = element.parentElement;
            const headerText = parentTh.textContent.replace(/[⇅↑↓]/g, '').trim();
            parentTh.innerHTML = headerText + ' <span style="cursor: pointer; color: #1976D2; font-size: 12px; margin-left: 4px;" onclick="sortCategoriaValoresTable(this, ' + columnIndex + ')" title="Clique para ordenar" data-sort="' + (isAscending ? 'asc' : 'desc') + '">' + 
                (isAscending ? '↑' : '↓') + '</span>';
            
            // Função para converter valor formatado em milhões para número
            function parseValueMilhoesBR(text) {
                if (!text || text.trim() === '' || text.trim() === '-') return 0;
                
                // Remover pontos de separação de milhares e converter vírgula para ponto decimal
                let cleanText = text.replace(/\./g, '').replace(',', '.').replace(/\s/g, '').trim();
                
                const value = parseFloat(cleanText) || 0;
                return value;
            }
            
            // Função para ordenação alfabética
            function compareText(a, b) {
                const textA = (a || '').toString().toLowerCase();
                const textB = (b || '').toString().toLowerCase();
                if (textA < textB) return -1;
                if (textA > textB) return 1;
                return 0;
            }
            
            // Ordenar baseado no tipo de coluna
            dataRows.sort(function(a, b) {
                const aText = a.cells[columnIndex].textContent || a.cells[columnIndex].innerText;
                const bText = b.cells[columnIndex].textContent || b.cells[columnIndex].innerText;
                
                // Para primeira coluna (regiões), usar ordenação alfabética
                if (columnIndex === 0) {
                    const comparison = compareText(aText, bText);
                    return isAscending ? comparison : -comparison;
                } else {
                    // Para colunas de valores em milhões, usar parseValueMilhoesBR
                    const aValue = parseValueMilhoesBR(aText);
                    const bValue = parseValueMilhoesBR(bText);
                    return isAscending ? aValue - bValue : bValue - aValue;
                }
            });
            
            // Limpar tbody e adicionar linhas ordenadas
            tbody.innerHTML = '';
            dataRows.forEach(row => tbody.appendChild(row));
            if (totalRow) tbody.appendChild(totalRow);
        }

function applyTrendColorsYearly() {
    document.querySelectorAll('table.yearly-table').forEach(table => {
        const rows = table.tBodies[0] ? Array.from(table.tBodies[0].rows) : [];
        let prev = null;
        rows.forEach(tr => {
            // second cell is the "Valor"
            const td = tr.cells && tr.cells.length > 1 ? tr.cells[1] : null;
            if (!td) return;
            const val = parseNumberBR(td.textContent);
            if (!isNaN(val)) {
                if (prev === null) {
                    td.classList.add('positive');
                } else if (val > prev) {
                    td.classList.add('positive');
                } else if (val < prev) {
                    td.classList.add('negative');
                } else {
                    td.classList.add('neutral');
                }
                prev = val;
            }
        });
    });
}

function applyTrendColorsAll() {
    applyTrendColorsQuarterly();
    applyTrendColorsYearly();
}
// re-apply after DOM updates
setTimeout(applyTrendColorsAll, 0);
// === helpers ===============================================================

// desenha texto colorido parte-a-parte (mantém cores das <span>)
function drawRichLine(doc, x, y, parts, baseFontSize) {
  let cursorX = x;
  doc.setFontSize(baseFontSize || 9);
  parts.forEach(p => {
    doc.setTextColor(p.color[0], p.color[1], p.color[2]);
    doc.text(p.text, cursorX, y);
    cursorX += doc.getTextWidth(p.text + ' ');
  });
  doc.setTextColor(0, 0, 0); // reset
  return cursorX;
}

// extrai a nota “Trimestre incompleto / Ano incompleto” de dentro do card
function findIncompleteNote(cardEl) {
  const divs = Array.from(cardEl.querySelectorAll('div'));
  for (const d of divs) {
    const t = (d.innerText || '').trim();
    if (/Trimestre incompleto|Ano incompleto/i.test(t)) return t;
  }
  return null;
}

function exportAllTablesToPDF(tipoImovel) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "mm", "a4");

  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const margin = 14;
  const line = 5.2;

  function ensureSpace(mmNeeded) {
    if (y + mmNeeded > pageH - margin) {
      doc.addPage();
      y = margin;
      tablesOnPage = 0;
    }
  }

  function drawVariationToken(token, x, y) {
    token = token.trim();
    const m = token.match(/^(.*?)([-+]?\d+,\d+%)\s*(.*)$/);
    if (!m) {
      doc.setTextColor(0,0,0);
      doc.text(token, x, y);
      return x + doc.getTextWidth(token + "  ");
    }
    const [_, prefix, pct, suffix] = m;

    // prefixo
    doc.setTextColor(0,0,0);
    if (prefix.trim()) {
      doc.text(prefix.trim() + " ", x, y);
      x += doc.getTextWidth(prefix.trim() + " ");
    }
    // percentual colorido
    const num = parseFloat(pct.replace("%","").replace(",", "."));
    if (num >= 0) doc.setTextColor(0,150,0);
    else doc.setTextColor(200,0,0);
    doc.text(pct, x, y);
    x += doc.getTextWidth(pct + " ");
    // sufixo
    if (suffix.trim()) {
      doc.setTextColor(0,0,0);
      doc.text(suffix.trim(), x, y);
      x += doc.getTextWidth(suffix.trim() + " ");
    }
    return x + doc.getTextWidth("  ");
  }

  const tipo = tipoImovel || (typeof currentView !== "undefined"
      ? (currentView === "residencial" ? "Residencial" : "Comercial")
      : "Residencial");

  let y = margin;

  // Título
  doc.setFont("helvetica", "normal");
  if (doc.setCharSpace) doc.setCharSpace(0);
  doc.setFontSize(18);
  
  let tituloRelatorio;
  if (typeof currentView !== "undefined" && currentView === 'crosstabs') {
    tituloRelatorio = `Relatório - Crosstabs (Residencial)`;
  } else {
    tituloRelatorio = `Relatório - Dashboard IVV (${tipo})`;
  }
  
  doc.text(tituloRelatorio, margin, y);
  y += 8;

  // Data
  doc.setFontSize(10);
  doc.text("Gerado em: " + new Date().toLocaleString("pt-BR"), margin, y);
  y += 6;

  // Filtros - Captura mais detalhada
  let f;
  if (typeof currentView !== "undefined" && currentView === 'crosstabs') {
    // Para crosstabs, usar função específica
    f = getCrossTabsFilters();
  } else {
    // Para outras views, usar função padrão
    f = getSelectedFilters();
  }
  
  const partes = [];
  
  // Verificar cada tipo de filtro com mais detalhes
  if (f.faixaValor?.length) {
    const textoFaixaValor = f.faixaValor.length === 1 ? f.faixaValor[0] : `${f.faixaValor.length} selecionadas (${f.faixaValor.join(", ")})`;
    partes.push("Faixa de Valor: " + textoFaixaValor);
  }
  
  if (f.faixaArea?.length) {
    const textoFaixaArea = f.faixaArea.length === 1 ? f.faixaArea[0] : `${f.faixaArea.length} selecionadas (${f.faixaArea.join(", ")})`;
    partes.push("Área Privativa: " + textoFaixaArea);
  }
  
  if (f.estagioObra?.length) {
    const textoEstagio = f.estagioObra.length === 1 ? f.estagioObra[0] : `${f.estagioObra.length} selecionados (${f.estagioObra.join(", ")})`;
    partes.push("Estágio da Obra: " + textoEstagio);
  }
  
  if (f.bairro?.length) {
    const textoBairro = f.bairro.length === 1 ? f.bairro[0] : `${f.bairro.length} selecionados (${f.bairro.slice(0, 5).join(", ")}${f.bairro.length > 5 ? ', ...' : ''})`;
    partes.push("Região Administrativa: " + textoBairro);
  }
  
  if (f.quartos?.length) {
    const textoQuartos = f.quartos.join(", ");
    partes.push("Quartos: " + textoQuartos);
  }
  
  // Para crosstabs, incluir período selecionado
  if (typeof currentView !== "undefined" && currentView === 'crosstabs' && f.periodo) {
    partes.push("Período: " + f.periodo);
  }



  const filtrosTexto = partes.length
    ? "Filtros e configurações aplicadas: " + partes.join(" | ")
    : "Nenhum filtro aplicado";

  if (doc.setCharSpace) doc.setCharSpace(0);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  if (doc.setCharSpace) doc.setCharSpace(0);

  const filtrosLinhas = doc.splitTextToSize(filtrosTexto, pageW - margin*2);
  filtrosLinhas.forEach((ln, i) => {
    doc.text(ln, margin, y + i * line);
  });

  y += filtrosLinhas.length * line + 6;

  // Determinar qual view está ativa e capturar apenas tabelas relevantes
  let cards;
  if (typeof currentView !== "undefined" && currentView === 'crosstabs') {
    // Para Crosstabs: pegar TODAS as tabelas do crossTablesContainer, não apenas as visíveis
    const crossContainer = document.getElementById('crossTablesContainer');
    if (crossContainer && crossContainer.style.display !== 'none') {
      // MUDANÇA: Incluir TODAS as tabelas cross-group, não filtrar por visibilidade
      const allCrossCards = crossContainer.querySelectorAll(".table-card.cross-group");
      cards = Array.from(allCrossCards); // Remover filtro de visibilidade
      console.log(`PDF Export: Incluindo TODAS as ${cards.length} tabelas do Crosstabs (não apenas as visíveis)`);
    } else {
      cards = [];
      console.log('PDF Export: crossTablesContainer não visível');
    }
  } else {
    // Para outras views: pegar TODAS as tabelas do tablesContainer, não apenas as visíveis
    const tablesContainer = document.getElementById('tablesContainer');
    if (tablesContainer && tablesContainer.style.display !== 'none') {
      // MUDANÇA: Incluir TODAS as tabelas, não filtrar por visibilidade
      const allCards = tablesContainer.querySelectorAll(".table-card");
      cards = Array.from(allCards); // Remover filtro de visibilidade
      console.log(`PDF Export: Incluindo TODAS as ${cards.length} tabelas da view ${currentView || 'padrão'} (não apenas as visíveis)`);
    } else {
      cards = [];
      console.log('PDF Export: tablesContainer não visível');
    }
  }
  
  let tablesOnPage = 0;

  cards.forEach((card, idx) => {
    if (tablesOnPage >= 3) {
      doc.addPage();
      y = margin;
      tablesOnPage = 0;
    }

    const titulo = (card.querySelector(".table-title")?.innerText || `Tabela ${idx+1}`).trim();
    console.log(`Exportando tabela: ${titulo}`);
    ensureSpace(10);
    doc.setFont("helvetica", "normal");
    if (doc.setCharSpace) doc.setCharSpace(0);
    doc.setFontSize(14);
    doc.setTextColor(0,0,0);
    doc.text(titulo, margin, y);
    y += 7;

    const table = card.querySelector("table");
    if (table) {
      ensureSpace(20);
      
      // Clonar tabela para limpar as setas antes de exportar
      const tableClone = table.cloneNode(true);
      
      // Remover setas (▲▼) e barras de fundo de todas as células
      tableClone.querySelectorAll('td').forEach(td => {
        // Remover spans com setas
        td.querySelectorAll('span').forEach(span => {
          const text = span.textContent;
          if (text === '▲' || text === '▼') {
            span.remove();
          }
        });
        
        // Remover divs de wrapper das barras
        const wrapper = td.querySelector('div[style*="position: relative"]');
        if (wrapper) {
          const valueText = wrapper.querySelector('div[style*="z-index: 1"]');
          if (valueText) {
            td.innerHTML = valueText.innerHTML;
          }
        }
      });
      
      doc.autoTable({
        html: tableClone,
        startY: y,
        margin: { left: margin, right: margin },
        styles: { fontSize: 8, halign: 'center', valign: 'middle', cellPadding: 1.5 },
        headStyles: { fillColor: [25, 118, 210], halign: 'center', valign: 'middle', textColor: 255 },
        theme: 'grid',
        tableLineColor: [230,230,230],
        tableLineWidth: 0.1
      });
      y = (doc.lastAutoTable && doc.lastAutoTable.finalY) ? doc.lastAutoTable.finalY + 5 : y + 5;
    }

    // Rodapé: variações + incompletude
    const varEl = card.querySelector(".variation-info");
    const incNode = Array.from(card.querySelectorAll("div, span, small, em"))
      .find(el => /incomplet/i.test(el.textContent));
    const variacaoLinha = varEl ? varEl.innerText.trim() : "";
    const incompletoLinha = incNode ? incNode.textContent.trim() : "";

    if (variacaoLinha || incompletoLinha) {
      ensureSpace(8);
      doc.setFontSize(10);
      if (doc.setCharSpace) doc.setCharSpace(0);

      let x = margin;
      doc.setTextColor(0,0,0);
      const tokens = variacaoLinha ? variacaoLinha.split("|") : [];
      tokens.forEach((tok, i) => {
        x = drawVariationToken(tok, x, y);
        if (i < tokens.length - 1) {
          doc.setTextColor(0,0,0);
          doc.text("|", x, y);
          x += doc.getTextWidth("| ") + 0.5;
        }
      });

      if (incompletoLinha) {
        doc.setTextColor(25,118,210);
        doc.text(incompletoLinha, pageW - margin, y, { align: "right" });
      }

      y += 9;
    } else {
      y += 5;
    }

    tablesOnPage++;
  });

  doc.setFontSize(8);
  doc.setTextColor(0,0,0);
  if (doc.setCharSpace) doc.setCharSpace(0);

  // Texto antes do link
  doc.text("Elaborado por ", margin, pageH - 8);

  // Texto com link
  doc.textWithLink("Opinião Informação Estratégica", margin + 35, pageH - 8, {
    url: "https://www.opiniao.inf.br"
  });

  // Texto depois do link
  doc.text(". Reprodução Proibida.", margin + 105, pageH - 8);

  const now = new Date();
  let nome;
  if (typeof currentView !== "undefined" && currentView === 'crosstabs') {
    nome = `Relatorio_Completo_Crosstabs_${now.getFullYear()}_${String(now.getMonth()+1).padStart(2,'0')}.pdf`;
  } else {
    nome = `Relatorio_Completo_${tipo}_${now.getFullYear()}_${String(now.getMonth()+1).padStart(2,'0')}.pdf`;
  }
  doc.save(nome);
}


"""
                
        return js_code

    
    def debug_january_2021(self):
        """
        Método de debug para analisar especificamente janeiro 2021
        """
        if self.residential_data is None or self.residential_data.empty:
            print("Nenhum dado residencial para debug")
            return
        
        period_2021_01 = 202101
        
        print(f"\n=== DEBUG JANEIRO 2021 (período {period_2021_01}) ===")
        
        # 1. Dados brutos do período
        jan_data = self.residential_data[self.residential_data['ANO_MES'] == period_2021_01]
        print(f"Total de linhas para Jan/2021: {len(jan_data)}")
        
        # 2. Lançamentos no período
        jan_launches = jan_data[jan_data['OFERTA_VENDA'] == 'OFERTADOS LANCAMENTOS']
        print(f"Linhas de lançamentos: {len(jan_launches)}")
        print(f"Total de unidades (soma bruta): {jan_launches['QUANTIDADE'].sum()}")
        
        # 3. Usar função original count_unique_projects
        original_count = self.count_unique_projects(self.residential_data)
        jan_projects_original = original_count.get(period_2021_01, 0)
        print(f"Empreendimentos únicos (função original): {jan_projects_original}")
        
        # 4. Usar get_projects_details
        details = self.get_projects_details(self.residential_data)
        jan_details = details.get(period_2021_01, [])
        print(f"Empreendimentos únicos (get_projects_details): {len(jan_details)}")
        
        # 5. Mostrar detalhes dos empreendimentos
        print("\nEmpreendimentos encontrados:")
        for i, project in enumerate(jan_details[:10]):  # Mostrar até 10
            print(f"  {i+1}. {project}")
        
        if len(jan_details) > 10:
            print(f"  ... e mais {len(jan_details) - 10} empreendimentos")
        
        # 6. Usar nova lógica de contagem
        new_counts = self.launch_manager.get_public_launch_counts(self.residential_data)
        jan_units_new = new_counts["monthly_units"].get(period_2021_01, 0)
        jan_projects_new = new_counts["monthly_projects"].get(period_2021_01, 0)
        
        print(f"\nNova lógica:")
        print(f"  Unidades: {jan_units_new}")
        print(f"  Empreendimentos: {jan_projects_new}")
        
        print("\n=== FIM DEBUG ===\n")


    
    def validate_html_txt_consistency(self):
        """
        Valida se contagens HTML e TXT são consistentes
        """
        if self.residential_data is None or self.residential_data.empty:
            print("Nenhum dado residencial para validar")
            return
        
        print("\n=== VALIDAÇÃO CONSISTÊNCIA HTML vs TXT ===")
        
        # Contagem HTML (via LaunchDataManager)
        html_counts = self.launch_manager.get_public_launch_counts(self.residential_data)
        
        # Contagem TXT (via get_projects_details)
        txt_details = self.launch_manager.get_private_launch_details(self.residential_data)
        
        # Verificar alguns períodos específicos
        test_periods = [202101, 202102, 202103]  # Jan, Fev, Mar 2021
        
        for period in test_periods:
            html_units = html_counts["monthly_units"].get(period, 0)
            html_projects = html_counts["monthly_projects"].get(period, 0)
            
            txt_projects = len(txt_details.get(period, []))
            
            period_str = f"{period//100}/{period%100:02d}"
            
            print(f"\n{period_str}:")
            print(f"  HTML: {html_units} unidades, {html_projects} empreendimentos")
            print(f"  TXT:  {txt_projects} empreendimentos")
            
            if html_projects == txt_projects:
                print(f"  ✅ Empreendimentos consistentes")
            else:
                print(f"  ❌ INCONSISTÊNCIA: HTML={html_projects}, TXT={txt_projects}")
            
            # Mostrar detalhes dos empreendimentos
            if period in txt_details:
                print(f"  Empreendimentos no TXT:")
                for i, project in enumerate(txt_details[period][:3]):  # Mostrar até 3
                    print(f"    {i+1}. {project[0]} | {project[1]} | {project[2]}")
                if len(txt_details[period]) > 3:
                    print(f"    ... e mais {len(txt_details[period]) - 3}")
        
        print("\n=== FIM VALIDAÇÃO ===\n")


    
    def comprehensive_launch_debug(self):
        """
        Debug abrangente de toda a cadeia de contagem de lançamentos
        """
        if self.residential_data is None or self.residential_data.empty:
            print("Nenhum dado residencial para debug")
            return
        
        period_test = 202101  # Janeiro 2021
        
        print("\n" + "="*70)
        print("DEBUG ABRANGENTE DA CONTAGEM DE LANÇAMENTOS")
        print("="*70)
        print(f"Período de teste: {period_test} (Jan/2021)")
        
        # PASSO 1: Verificar get_projects_details (função que gera TXT)
        print("\n1️⃣ FUNÇÃO get_projects_details (base do TXT):")
        txt_details = self.get_projects_details(self.residential_data)
        jan_txt_details = txt_details.get(period_test, [])
        print(f"   Empreendimentos encontrados: {len(jan_txt_details)}")
        
        if jan_txt_details:
            print("   Primeiros 3 empreendimentos:")
            for i, project in enumerate(jan_txt_details[:3]):
                print(f"     {i+1}. {project}")
        
        # PASSO 2: Verificar LaunchDataManager
        print("\n2️⃣ LAUNCH DATA MANAGER:")
        html_counts = self.launch_manager.get_public_launch_counts(self.residential_data)
        jan_html_units = html_counts["monthly_units"].get(period_test, 0)
        jan_html_projects = html_counts["monthly_projects"].get(period_test, 0)
        print(f"   Unidades calculadas: {jan_html_units}")
        print(f"   Empreendimentos calculados: {jan_html_projects}")
        
        # PASSO 3: Verificar JSON gerado
        print("\n3️⃣ JSON GERADO PARA JAVASCRIPT:")
        projects_count_empreendimentos = {
            "residencial": html_counts["monthly_projects"],
            "residencial_quarterly": html_counts["quarterly_projects"],
            "residencial_yearly": html_counts["yearly_projects"],
        }
        json_content = json.dumps(projects_count_empreendimentos, ensure_ascii=False)
        print(f"   JSON residencial (Jan 2021): {projects_count_empreendimentos['residencial'].get(period_test, 'N/A')}")
        
        # PASSO 4: Verificar dados brutos do período
        print("\n4️⃣ DADOS BRUTOS DO PERÍODO:")
        jan_data = self.residential_data[self.residential_data['ANO_MES'] == period_test]
        jan_launches = jan_data[jan_data['OFERTA_VENDA'] == 'OFERTADOS LANCAMENTOS']
        print(f"   Total de linhas no período: {len(jan_data)}")
        print(f"   Linhas de lançamentos: {len(jan_launches)}")
        print(f"   Soma bruta de unidades: {jan_launches['QUANTIDADE'].sum()}")
        
        # PASSO 5: Verificar empreendimentos únicos
        print("\n5️⃣ ANÁLISE DE EMPREENDIMENTOS ÚNICOS:")
        jan_with_emp = self.extract_empreendimento_name(jan_launches.copy())
        unique_combinations = jan_with_emp.drop_duplicates(
            subset=['EMPREENDIMENTO_AGRUPADO', 'EMPRESA', 'BAIRRO']
        )
        print(f"   Combinações únicas (EMP+EMPRESA+BAIRRO): {len(unique_combinations)}")
        
        if len(unique_combinations) > 0:
            print("   Primeiras 5 combinações:")
            for i, row in unique_combinations.head().iterrows():
                emp = row.get('EMPREENDIMENTO_AGRUPADO', 'N/A')
                empresa = row.get('EMPRESA', 'N/A')
                bairro = row.get('BAIRRO', 'N/A')
                qtd = row.get('QUANTIDADE', 0)
                print(f"     {emp} | {empresa} | {bairro} | {qtd} unids")
        
        # PASSO 6: Comparação final
        print("\n6️⃣ COMPARAÇÃO FINAL:")
        print(f"   TXT (get_projects_details): {len(jan_txt_details)} empreendimentos")
        print(f"   HTML (LaunchDataManager): {jan_html_projects} empreendimentos")
        print(f"   Dados brutos únicos: {len(unique_combinations)} combinações")
        
        if len(jan_txt_details) == jan_html_projects:
            print("   ✅ HTML e TXT consistentes!")
        else:
            print("   ❌ INCONSISTÊNCIA detectada!")
            print("\n🔍 DIAGNÓSTICO:")
            if jan_html_projects == len(unique_combinations):
                print("   - HTML conta combinações brutas (sem filtro de primeira aparição)")
                print("   - TXT usa filtro de primeira aparição histórica")
                print("   - SOLUÇÃO: HTML deve usar mesma lógica do TXT")
            else:
                print("   - Lógicas completamente diferentes")
                print("   - Necessária revisão completa da sincronização")
        
        print("\n" + "="*70)
        print("FIM DO DEBUG ABRANGENTE")
        print("="*70 + "\n")


    def run(self, input_file=None, output_file=None):
        """Executa o processamento completo"""
        if not input_file:
            input_file = self.select_input_file()
            if not input_file:
                print("Nenhum arquivo selecionado. Saindo...")
                return False
        
        if not output_file:
            input_dir = os.path.dirname(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(input_dir, f"Dashboard_Imobiliario_{timestamp}.html")
        
        if not self.load_data(input_file):
            return False
        
        # 🔹 Gera o HTML
        html_content = self.generate_html_template()
        
        try:
            # Salva HTML
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Dashboard HTML gerado com sucesso: {output_file}")

            # 🔹 Gera TXT de lançamentos residenciais
            # 🔹 MODIFICADO: Gera TXT usando gerenciador de lançamentos
            try:
                residential_details = self.launch_manager.get_private_launch_details(self.residential_data)
                txt_file_res = os.path.join(os.path.dirname(output_file), "lancamentos_residenciais.txt")
                self.launch_manager.generate_private_txt_report(residential_details, txt_file_res)
                print(f"Arquivo TXT de lançamentos residenciais gerado com sucesso: {txt_file_res}")

                commercial_details = self.launch_manager.get_private_launch_details(self.commercial_data)
                txt_file_com = os.path.join(os.path.dirname(output_file), "lancamentos_comerciais.txt")
                self.launch_manager.generate_private_txt_report(commercial_details, txt_file_com)
                print(f"Arquivo TXT de lançamentos comerciais gerado com sucesso: {txt_file_com}")
                return True

            except Exception as e:
                print(f"Erro ao salvar arquivo HTML ou TXT: {e}")
                return False

            return True

        except Exception as e:
            print(f"Erro ao salvar arquivo HTML ou TXT: {e}")
            return False


# ==================== PONTO DE ENTRADA ====================


    def validate_launch_data_separation(self):
        """
        Valida se a separação de dados está funcionando corretamente
        """
        if self.residential_data is None or self.residential_data.empty:
            print("⚠️  Nenhum dado residencial para validar")
            return
        
        # Teste 1: Dados públicos não devem conter informações sensíveis
        public_json = json.dumps(self.prepare_data_for_json(self.residential_data))
        sensitive_terms = ['CONSTRUTORA', 'INCORPORAÇÕES', 'LTDA', 'S.A.']
        
        found_sensitive = []
        for term in sensitive_terms:
            if term.upper() in public_json.upper():
                found_sensitive.append(term)
        
        if found_sensitive:
            print(f"❌ VAZAMENTO DETECTADO: {found_sensitive}")
        else:
            print("✅ Dados públicos limpos - sem informações sensíveis")
        
        # Teste 2: Consistência entre contagens públicas e privadas
        public_counts = self.launch_manager.get_public_launch_counts(self.residential_data)
        private_details = self.launch_manager.get_private_launch_details(self.residential_data)
        
        public_total = sum(public_counts["monthly"].values())
        private_total = len([emps for period_emps in private_details.values() for emps in period_emps])
        
        print(f"📊 Total lançamentos público: {public_total} unidades")
        print(f"📊 Total empreendimentos privado: {private_total}")
        
        if abs(public_total - private_total) < 50:  # Tolerância para diferenças de cálculo
            print("✅ Consistência entre dados públicos e privados")
        else:
            print("❌ Inconsistência detectada entre dados públicos e privados")

def load_permissions_config():
    """Carrega configurações de permissões do JSON"""
    try:
        with open('dashboard_permissions.json', 'r') as f:
            return json.load(f)
    except:
        # Se não existir, usar padrão
        return {
            'permissions': {
                'admin': {'menus': ['residencial','comercial','crosstabs','insights']},
                'manager': {'menus': ['residencial','comercial']},
                'analyst': {'menus': ['residencial']},
                'viewer': {'menus': ['residencial']}
            }
        }

def main():
    """Função principal com suporte a perfis e geração múltipla"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gerador de Dashboard Imobiliário')
    parser.add_argument('input_file', nargs='?', help='Arquivo Excel de entrada')
    parser.add_argument('output_file', nargs='?', help='Arquivo HTML de saída')
    parser.add_argument('--profile', choices=['admin', 'manager', 'analyst', 'viewer'], 
                       help='Perfil específico para gerar dashboard')
    parser.add_argument('--todos-perfis', action='store_true', 
                       help='Gera dashboard para todos os perfis configurados')
    
    args = parser.parse_args()
    
    if args.todos_perfis:
        # Gerar para todos os perfis
        print("🔄 Gerando dashboards para todos os perfis...")
        
        # Seleciona arquivo Excel uma vez
        temp_generator = DashboardGenerator()
        input_file = args.input_file or temp_generator.select_input_file()
        if not input_file:
            print("Nenhum arquivo selecionado. Saindo...")
            return
        
        # Gera para cada perfil
        for profile in ['admin', 'manager', 'analyst', 'viewer']:
            print(f"\n📊 Gerando dashboard para perfil: {profile}")
            
            # Busca usuário real com esse perfil
            user_email = temp_generator.get_user_by_profile(profile)
            
            if not user_email:
                print(f"⚠️ Pulando {profile} - nenhum usuário encontrado")
                continue
            
            # Cria generator com usuário encontrado
            profile_generator = DashboardGenerator(user_email)
            
            output_file = f"templates/dashboard_{profile}.html"
            success = profile_generator.run(input_file, output_file)
            
            if success:
                print(f"  ✅ {output_file} gerado com sucesso!")
            else:
                print(f"  ❌ Erro ao gerar {output_file}")
                
        print("\n🎉 Todos os dashboards gerados!")        

    elif args.profile:
        # Gerar para perfil específico
        print(f"🎯 Gerando dashboard para perfil: {args.profile}")
        
        # Busca usuário real com esse perfil no sistema
        temp_generator = DashboardGenerator()
        user_email = temp_generator.get_user_by_profile(args.profile)
        
        if not user_email:
            print("❌ Não foi possível encontrar usuário para este perfil")
            return
        
        # Cria generator com usuário real encontrado
        generator = DashboardGenerator(user_email)
        
        # Determina arquivos
        input_file = args.input_file or generator.select_input_file()
        if not input_file:
            print("Nenhum arquivo selecionado. Saindo...")
            return
        
        if args.output_file:
            output_file = args.output_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"Dashboard_Imobiliario_{args.profile}_{timestamp}.html"
        
        success = generator.run(input_file, output_file)
        
        if success:
            print(f"✅ Dashboard gerado: {output_file}")
            print(f"💡 Para usar no Flask: mv {output_file} templates/dashboard_{args.profile}.html")
        else:
            print(f"❌ Erro na geração do dashboard")    

    else:
        # Comportamento normal (seu workflow original)
        generator = DashboardGenerator()
        
        input_file = args.input_file or generator.select_input_file()
        output_file = args.output_file
        
        if input_file:
            generator.run(input_file, output_file)
            
if __name__ == "__main__":
    main()
# FASE 3 INICIADA EM Qua  8 Out 2025 22:39:56 -03
