import tkinter as tk
from tkinter import ttk
import re

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

    def create_output(self, title):
        frame = ttk.LabelFrame(self.root, text=title)
        frame.pack(fill=tk.X, padx=10, pady=5)
        text = tk.Text(frame, height=5, fg='black')
        text.pack(fill=tk.X)
        return text

    def parse_sql(self, sql):
        partes = {"SELECT": "", "FROM": "", "JOIN": [], "WHERE": ""}
        # Remove comentários, quebras de linha e espaços extras
        sql = re.sub(r"\s+", " ", sql.strip())

        # Capturando as cláusulas SELECT e FROM
        select_match = re.search(r"SELECT (.+?) FROM", sql, re.IGNORECASE)
        from_match = re.search(r"FROM (\w+)", sql, re.IGNORECASE)
        if not select_match or not from_match:
            raise ValueError("Consulta SQL inválida: certifique-se de que a consulta contenha as cláusulas SELECT e FROM.")

        # Capturando possíveis JOINs e a cláusula WHERE (opcional)
        joins = re.findall(r"JOIN\s+(\w+)\s+ON\s+(.+?)(?=\s+JOIN|\s+WHERE|$)", sql, re.IGNORECASE)
        where_match = re.search(r"WHERE (.+)", sql, re.IGNORECASE)

        partes["SELECT"] = select_match.group(1).strip()
        partes["FROM"] = from_match.group(1).strip()
        if joins:
            partes["JOIN"] = [{"tabela": j[0], "condicao": j[1].strip()} for j in joins]
        if where_match:
            partes["WHERE"] = where_match.group(1).strip()

        return partes

    def executar_consulta(self):
        sql = self.sql_entry.get("1.0", tk.END).strip()
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        if not sql:
            self.relacional_text.delete("1.0", tk.END)
            self.relacional_text.insert(tk.END, "A consulta SQL está vazia. Por favor, insira uma consulta válida.")
            return

        try:
            partes = self.parse_sql(sql)
        except Exception as e:
            self.relacional_text.delete("1.0", tk.END)
            self.relacional_text.insert(tk.END, f"Erro: {str(e)}")
            return

        self.relacional_text.delete("1.0", tk.END)
        self.ordem_text.delete("1.0", tk.END)

        # Constrói a cadeia de junções com o mínimo de parênteses
        if partes["JOIN"]:
            join_chain = partes["FROM"] + " ⨝ " + " ⨝ ".join(
                [f"{j['tabela']} ON {j['condicao']}" for j in partes["JOIN"]]
            )
        else:
            join_chain = partes["FROM"]

        # Aplica a seleção se houver cláusula WHERE
        if partes["WHERE"]:
            relacao = f"σ({partes['WHERE']})({join_chain})"
        else:
            relacao = join_chain

        # Aplica a projeção final
        projecao = f"π({partes['SELECT']})({relacao})"

        self.relacional_text.insert(tk.END, projecao)

        ordem_execucao = (
            "1. Seleção (σ): Aplica os predicados da cláusula WHERE.\n"
            "2. Junção (⨝): Realiza as junções com as condições ON.\n"
            "3. Projeção (π): Seleciona os atributos desejados."
        )
        self.ordem_text.insert(tk.END, ordem_execucao)

if __name__ == "__main__":
    root = tk.Tk()
    app = SQLProcessorGUI(root)
    root.mainloop()
