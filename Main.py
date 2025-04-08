import tkinter as tk
from tkinter import ttk
import re
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

METADADOS = {
    "Categoria": ["idCategoria", "Descricao"],
    "Produto": ["idProduto", "Nome", "Descricao", "Preco", "QuantEstoque", "Categoria_idCategoria"],
    "TipoCliente": ["idTipoCliente", "Descricao"],
    "Cliente": ["idCliente", "Nome", "Email", "Nascimento", "Senha", "TipoCliente_idTipoCliente", "DataRegistro"],
    "TipoEndereco": ["idTipoEndereco", "Descricao"],
    "Endereco": [
        "idEndereco", "EnderecoPadrao", "Logradouro", "Numero", "Complemento", "Bairro", "Cidade",
        "UF", "CEP", "TipoEndereco_idTipoEndereco", "Cliente_idCliente"
    ],
    "Telefone": ["Numero", "Cliente_idCliente"],
    "Status": ["idStatus", "Descricao"],
    "Pedido": ["idPedido", "Status_idStatus", "DataPedido", "ValorTotalPedido", "Cliente_idCliente"],
    "Pedido_has_Produto": ["idPedidoProduto", "Pedido_idPedido", "Produto_idProduto", "Quantidade", "PrecoUnitario"]
}

class SQLProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Processador de Consultas SQL")

        ttk.Label(root, text="Consulta SQL:").pack()
        self.sql_entry = tk.Text(root, height=5)
        self.sql_entry.pack(fill=tk.X, padx=10)

        ttk.Button(root, text="Executar", command=self.executar_consulta).pack(pady=10)

        self.relacional_text = self.create_output("Álgebra Relacional")
        self.ordem_text = self.create_output("Ordem de Execução")
        self.plano_text = self.create_output("Plano de Execução")

        self.graph_frame = ttk.LabelFrame(root, text="Grafo de Operadores")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def create_output(self, title):
        frame = ttk.LabelFrame(self.root, text=title)
        frame.pack(fill=tk.X, padx=10, pady=5)
        text = tk.Text(frame, height=5, fg='black')
        text.pack(fill=tk.X)
        return text

    def parse_sql(self, sql):
        partes = {"SELECT": "", "FROM": "", "JOIN": [], "WHERE": ""}
        sql = re.sub(r"\s+", " ", sql.strip())

        select_match = re.search(r"SELECT (.+?) FROM", sql, re.IGNORECASE)
        from_match = re.search(r"FROM (\w+)", sql, re.IGNORECASE)
        joins = re.findall(r"JOIN (\w+) ON (.+?)(?: JOIN| WHERE|$)", sql, re.IGNORECASE)
        where_match = re.search(r"WHERE (.+)", sql, re.IGNORECASE)

        if select_match:
            partes["SELECT"] = select_match.group(1).strip()
        if from_match:
            partes["FROM"] = from_match.group(1).strip()
        if joins:
            partes["JOIN"] = joins
        if where_match:
            partes["WHERE"] = where_match.group(1).strip()

        return partes

    def validar_tabelas_colunas(self, partes):
        erros = []
        tabelas_utilizadas = [partes["FROM"]] + [join[0] for join in partes["JOIN"]]

        # Converter METADADOS para minúsculas para comparação
        metadados_lower = {k.lower(): [c.lower() for c in v] for k, v in METADADOS.items()}

        for tabela in tabelas_utilizadas:
            if tabela.lower() not in metadados_lower:
                erros.append(f"Tabela não existe: {tabela}")

        colunas = [col.strip() for col in partes["SELECT"].split(",") if col.strip()]
        if colunas == ['*']:
            colunas = []

        for coluna in colunas:
            if '.' in coluna:
                tabela_ref, col_ref = coluna.split('.')
                if tabela_ref.lower() not in metadados_lower or col_ref.lower() not in metadados_lower[tabela_ref.lower()]:
                    erros.append(f"Coluna inválida: {coluna}")
            else:
                if not any(coluna.lower() in metadados_lower[t] for t in metadados_lower):
                    erros.append(f"Coluna inválida: {coluna}")

        if partes["WHERE"]:
            condicoes = re.split(r"\s+AND\s+|\s+OR\s+", partes["WHERE"], flags=re.IGNORECASE)
            for cond in condicoes:
                col = re.split(r"\s*[<>=!]+\s*", cond.strip())[0]
                col = col.strip()
                if '.' in col:
                    tabela_ref, col_ref = col.split('.')
                    if tabela_ref.lower() not in metadados_lower or col_ref.lower() not in metadados_lower[tabela_ref.lower()]:
                        erros.append(f"Coluna inválida no WHERE: {col}")
                else:
                    if not any(col.lower() in metadados_lower[t] for t in metadados_lower):
                        erros.append(f"Coluna inválida no WHERE: {col}")

        return erros

    def desenhar_grafo(self, partes):
        G = nx.DiGraph()

        base = partes["FROM"]
        G.add_node(base)

        for tabela, cond in partes["JOIN"]:
            G.add_node(tabela)
            G.add_edge(base, tabela, label=f"JOIN ON {cond}")
            base = tabela

        if partes["WHERE"]:
            G.add_node("σ (seleção)")
            G.add_edge("σ (seleção)", base, label=partes["WHERE"])
            base = "σ (seleção)"

        G.add_node("π (projeção)")
        G.add_edge("π (projeção)", base)

        fig = plt.Figure(figsize=(7, 4))
        ax = fig.add_subplot(111)
        pos = nx.spring_layout(G, k=1.2)
        nx.draw(G, pos, ax=ax, with_labels=True, node_color="lightblue", node_size=2000, font_size=9)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=8)

        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def executar_consulta(self):
        sql = self.sql_entry.get("1.0", tk.END).strip()
        if not sql:
            return

        partes = self.parse_sql(sql)
        erros = self.validar_tabelas_colunas(partes)

        self.relacional_text.delete("1.0", tk.END)
        self.ordem_text.delete("1.0", tk.END)
        self.plano_text.delete("1.0", tk.END)

        if erros:
            self.relacional_text.insert(tk.END, "[ERROS NA CONSULTA:]\n" + "\n".join(erros))
            self.relacional_text.config(fg='red')
            return
        else:
            self.relacional_text.config(fg='black')

        relacao_joins = ' ⨝ '.join([f"{join[0]}" for join in partes["JOIN"]]) or ""
        base = partes["FROM"] + (' ⨝ ' + relacao_joins if relacao_joins else "")

        where = f"σ({partes['WHERE']})" if partes["WHERE"] else ""
        projecao = f"π({partes['SELECT']})" if partes["SELECT"] else "π(*)"

        alg_rel = f"{projecao}({where}({base}))" if where else f"{projecao}({base})"

        self.relacional_text.insert(tk.END, alg_rel)
        self.ordem_text.insert(tk.END, "1. Seleção\n2. Junção\n3. Projeção")
        self.plano_text.insert(tk.END, f"Consulta válida com {len(partes['JOIN'])+1} tabela(s).")

        self.desenhar_grafo(partes)

if __name__ == "__main__":
    root = tk.Tk()
    app = SQLProcessorGUI(root)
    root.mainloop()
