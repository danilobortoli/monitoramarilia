"""
Modelos de banco de dados SQLite para armazenamento histórico.

Armazena dados coletados para:
- Análise histórica
- Geração de relatórios
- Detecção de tendências
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Diretório do banco de dados
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "monitoramarilia.db"


def get_connection() -> sqlite3.Connection:
    """Obtém conexão com o banco de dados."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Inicializa o banco de dados com as tabelas necessárias."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de coletas (metadados de cada execução)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fonte TEXT NOT NULL,
            ano_referencia INTEGER,
            periodo TEXT,
            sucesso BOOLEAN DEFAULT 1,
            registros INTEGER DEFAULT 0,
            observacao TEXT
        )
    """)

    # Tabela de indicadores fiscais (SICONFI)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indicadores_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coleta_id INTEGER,
            data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ano INTEGER NOT NULL,
            quadrimestre INTEGER,
            bimestre INTEGER,
            indicador TEXT NOT NULL,
            valor REAL,
            percentual_rcl REAL,
            limite REAL,
            status TEXT,
            fonte TEXT DEFAULT 'SICONFI',
            FOREIGN KEY (coleta_id) REFERENCES coletas(id)
        )
    """)

    # Tabela de despesas (TCE-SP)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coleta_id INTEGER,
            data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ano INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            orgao TEXT,
            unidade TEXT,
            evento TEXT,
            numero_empenho TEXT,
            fornecedor TEXT,
            cnpj_parcial TEXT,
            data_despesa TEXT,
            valor REAL,
            fonte TEXT DEFAULT 'TCE-SP',
            FOREIGN KEY (coleta_id) REFERENCES coletas(id)
        )
    """)

    # Tabela de fornecedores (consolidado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            nome TEXT NOT NULL,
            valor_total REAL DEFAULT 0,
            qtd_pagamentos INTEGER DEFAULT 0,
            percentual_total REAL,
            situacao_sancoes TEXT,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ano_referencia INTEGER
        )
    """)

    # Tabela de transferências federais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coleta_id INTEGER,
            data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ano INTEGER NOT NULL,
            tipo TEXT,
            valor REAL,
            descricao TEXT,
            fonte TEXT DEFAULT 'Portal Federal',
            FOREIGN KEY (coleta_id) REFERENCES coletas(id)
        )
    """)

    # Tabela de convênios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS convenios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coleta_id INTEGER,
            numero TEXT,
            objeto TEXT,
            valor_repasse REAL,
            valor_contrapartida REAL,
            situacao TEXT,
            orgao TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            ano INTEGER,
            FOREIGN KEY (coleta_id) REFERENCES coletas(id)
        )
    """)

    # Tabela de alertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL,
            categoria TEXT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            valor REAL,
            limite REAL,
            resolvido BOOLEAN DEFAULT 0,
            data_resolucao TIMESTAMP
        )
    """)

    # Tabela de relatórios gerados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            periodo TEXT,
            arquivo_path TEXT,
            tamanho_bytes INTEGER,
            hash_arquivo TEXT
        )
    """)

    # Índices para performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_despesas_ano_mes ON despesas(ano, mes)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_despesas_fornecedor ON despesas(cnpj_parcial)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicadores_ano ON indicadores_fiscais(ano)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alertas_tipo ON alertas(tipo, resolvido)")

    conn.commit()
    conn.close()

    print(f"Banco de dados inicializado em: {DB_PATH}")


class DatabaseManager:
    """Gerenciador de operações no banco de dados."""

    def __init__(self):
        """Inicializa o gerenciador e cria tabelas se necessário."""
        init_database()

    def registrar_coleta(
        self,
        fonte: str,
        ano_referencia: int,
        periodo: str = None,
        sucesso: bool = True,
        registros: int = 0,
        observacao: str = None
    ) -> int:
        """
        Registra uma nova coleta de dados.

        Returns:
            ID da coleta registrada
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO coletas (fonte, ano_referencia, periodo, sucesso, registros, observacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fonte, ano_referencia, periodo, sucesso, registros, observacao))

        coleta_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return coleta_id

    def salvar_indicador_fiscal(
        self,
        coleta_id: int,
        ano: int,
        indicador: str,
        valor: float = None,
        percentual_rcl: float = None,
        limite: float = None,
        status: str = None,
        quadrimestre: int = None,
        bimestre: int = None
    ):
        """Salva um indicador fiscal no banco."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO indicadores_fiscais
            (coleta_id, ano, quadrimestre, bimestre, indicador, valor, percentual_rcl, limite, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (coleta_id, ano, quadrimestre, bimestre, indicador, valor, percentual_rcl, limite, status))

        conn.commit()
        conn.close()

    def salvar_despesas(self, coleta_id: int, despesas: List[Dict[str, Any]]):
        """Salva lista de despesas no banco."""
        conn = get_connection()
        cursor = conn.cursor()

        for d in despesas:
            cursor.execute("""
                INSERT INTO despesas
                (coleta_id, ano, mes, orgao, unidade, evento, numero_empenho,
                 fornecedor, cnpj_parcial, data_despesa, valor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coleta_id,
                d.get("ano", datetime.now().year),
                d.get("mes", 1),
                d.get("orgao", ""),
                d.get("unidade", ""),
                d.get("evento", ""),
                d.get("numero_empenho", ""),
                d.get("fornecedor", ""),
                d.get("cnpj_parcial", ""),
                d.get("data", ""),
                d.get("valor", 0)
            ))

        conn.commit()
        conn.close()

    def atualizar_fornecedores(self, ano: int, fornecedores: List[Dict[str, Any]]):
        """Atualiza tabela de fornecedores consolidados."""
        conn = get_connection()
        cursor = conn.cursor()

        for f in fornecedores:
            # Verificar se já existe
            cursor.execute("""
                SELECT id FROM fornecedores
                WHERE cnpj = ? AND ano_referencia = ?
            """, (f.get("cnpj_parcial", ""), ano))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE fornecedores
                    SET nome = ?, valor_total = ?, qtd_pagamentos = ?,
                        percentual_total = ?, situacao_sancoes = ?,
                        ultima_atualizacao = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    f.get("fornecedor", f.get("nome", "")),
                    f.get("valor_total", f.get("valor", 0)),
                    f.get("qtd_pagamentos", 0),
                    f.get("percentual", 0),
                    f.get("situacaoSancoes", "NAO_VERIFICADO"),
                    existing["id"]
                ))
            else:
                cursor.execute("""
                    INSERT INTO fornecedores
                    (cnpj, nome, valor_total, qtd_pagamentos, percentual_total,
                     situacao_sancoes, ano_referencia)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f.get("cnpj_parcial", f.get("cnpj", "")),
                    f.get("fornecedor", f.get("nome", "")),
                    f.get("valor_total", f.get("valor", 0)),
                    f.get("qtd_pagamentos", 0),
                    f.get("percentual", 0),
                    f.get("situacaoSancoes", "NAO_VERIFICADO"),
                    ano
                ))

        conn.commit()
        conn.close()

    def salvar_alerta(
        self,
        tipo: str,
        titulo: str,
        descricao: str = None,
        categoria: str = None,
        valor: float = None,
        limite: float = None
    ):
        """Salva um alerta no banco."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alertas (tipo, categoria, titulo, descricao, valor, limite)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tipo, categoria, titulo, descricao, valor, limite))

        conn.commit()
        conn.close()

    def registrar_relatorio(
        self,
        tipo: str,
        titulo: str,
        arquivo_path: str,
        periodo: str = None,
        tamanho_bytes: int = None
    ) -> int:
        """Registra um relatório gerado."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO relatorios (tipo, titulo, periodo, arquivo_path, tamanho_bytes)
            VALUES (?, ?, ?, ?, ?)
        """, (tipo, titulo, periodo, arquivo_path, tamanho_bytes))

        relatorio_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return relatorio_id

    # Métodos de consulta

    def get_historico_indicador(self, indicador: str, anos: int = 5) -> List[Dict]:
        """Busca histórico de um indicador fiscal."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ano, quadrimestre, valor, percentual_rcl, status
            FROM indicadores_fiscais
            WHERE indicador LIKE ?
            ORDER BY ano DESC, quadrimestre DESC
            LIMIT ?
        """, (f"%{indicador}%", anos * 3))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_fornecedores_ranking(self, ano: int, top_n: int = 20) -> List[Dict]:
        """Retorna ranking de fornecedores."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cnpj, nome, valor_total, qtd_pagamentos,
                   percentual_total, situacao_sancoes
            FROM fornecedores
            WHERE ano_referencia = ?
            ORDER BY valor_total DESC
            LIMIT ?
        """, (ano, top_n))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_alertas_ativos(self) -> List[Dict]:
        """Retorna alertas não resolvidos."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM alertas
            WHERE resolvido = 0
            ORDER BY data_criacao DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_relatorios(self, tipo: str = None, limite: int = 10) -> List[Dict]:
        """Lista relatórios gerados."""
        conn = get_connection()
        cursor = conn.cursor()

        if tipo:
            cursor.execute("""
                SELECT * FROM relatorios
                WHERE tipo = ?
                ORDER BY data_geracao DESC
                LIMIT ?
            """, (tipo, limite))
        else:
            cursor.execute("""
                SELECT * FROM relatorios
                ORDER BY data_geracao DESC
                LIMIT ?
            """, (limite,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais do banco."""
        conn = get_connection()
        cursor = conn.cursor()

        stats = {}

        # Total de coletas
        cursor.execute("SELECT COUNT(*) as total FROM coletas")
        stats["total_coletas"] = cursor.fetchone()["total"]

        # Total de despesas
        cursor.execute("SELECT COUNT(*) as total FROM despesas")
        stats["total_despesas"] = cursor.fetchone()["total"]

        # Total de fornecedores
        cursor.execute("SELECT COUNT(*) as total FROM fornecedores")
        stats["total_fornecedores"] = cursor.fetchone()["total"]

        # Alertas ativos
        cursor.execute("SELECT COUNT(*) as total FROM alertas WHERE resolvido = 0")
        stats["alertas_ativos"] = cursor.fetchone()["total"]

        # Relatórios gerados
        cursor.execute("SELECT COUNT(*) as total FROM relatorios")
        stats["total_relatorios"] = cursor.fetchone()["total"]

        # Última coleta
        cursor.execute("SELECT MAX(data_coleta) as ultima FROM coletas")
        stats["ultima_coleta"] = cursor.fetchone()["ultima"]

        conn.close()

        return stats


# Inicializar banco ao importar o módulo
if __name__ == "__main__":
    init_database()
    db = DatabaseManager()
    print("Estatísticas:", db.get_estatisticas())
