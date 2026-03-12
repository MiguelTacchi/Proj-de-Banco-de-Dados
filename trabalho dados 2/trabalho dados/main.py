import math
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox



def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = int(math.isqrt(n))
    i = 3
    while i <= r:
        if n % i == 0:
            return False
        i += 2
    return True


def next_prime(x: int) -> int:
    if x <= 2:
        return 2
    n = x if x % 2 == 1 else x + 1
    while not is_prime(n):
        n += 2
    return n


# =========================
# Estrutura: Página (física)
# =========================
class Page:
    def __init__(self, page_id: int, records: list[str]):
        self.page_id = page_id
        self.records = records


class TableStorage:
    """
    Simula tabela em disco dividida em páginas.
    """
    def __init__(self):
        self.records: list[str] = []
        self.pages: list[Page] = []

    def load_file(self, path: str) -> int:
        self.records.clear()
        self.pages.clear()

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if w:
                    self.records.append(w)
        return len(self.records)

    def paginate(self, page_size: int) -> int:
        if page_size <= 0:
            raise ValueError("Tamanho da página deve ser > 0.")
        self.pages.clear()
        pid = 0
        for i in range(0, len(self.records), page_size):
            self.pages.append(Page(pid, self.records[i:i + page_size]))
            pid += 1
        return len(self.pages)

    def nr(self) -> int:
        return len(self.records)

    def page_count(self) -> int:
        return len(self.pages)

    def get_page(self, pid: int) -> Page:
        return self.pages[pid]

    def table_scan(self, key: str, max_log_lines: int = 2000):
        """
        Varre páginas até achar a chave.
        Retorna: found, page_id, pages_read, elapsed_ms, log(list[str])
        """
        if self.page_count() == 0:
            raise ValueError("Não há páginas. Faça a paginação antes.")

        t0 = time.perf_counter()
        log = []
        pages_read = 0

        for p in self.pages:
            pages_read += 1
            if len(log) < max_log_lines:
                log.append(f"Lendo Página P{p.page_id} ...")

            for rec in p.records:
                if len(log) < max_log_lines:
                    log.append(f"  {rec}")
                if rec == key:
                    if len(log) < max_log_lines:
                        log.append(f">> ENCONTROU em P{p.page_id}")
                    t1 = time.perf_counter()
                    return True, p.page_id, pages_read, (t1 - t0) * 1000.0, log

        if len(log) < max_log_lines:
            log.append(">> NÃO ENCONTRADO")
        t1 = time.perf_counter()
        return False, -1, pages_read, (t1 - t0) * 1000.0, log


# =========================
# Estruturas: Bucket + Overflow
# =========================
class BucketEntry:
    def __init__(self, key: str, page_id: int):
        self.key = key
        self.page_id = page_id


class OverflowPage:
    def __init__(self, capacity_fr: int):
        self.capacity_fr = capacity_fr
        self.entries: list[BucketEntry] = []
        self.next: "OverflowPage | None" = None

    def has_space(self) -> bool:
        return len(self.entries) < self.capacity_fr


class Bucket:
    def __init__(self, bucket_id: int, fr: int):
        self.bucket_id = bucket_id
        self.fr = fr
        self.primary: list[BucketEntry] = []
        self.overflow_head: OverflowPage | None = None

    def insert(self, entry: BucketEntry) -> tuple[bool, bool]:
        """
        Retorna (collision, overflowed)
        """
        collision = (len(self.primary) > 0) or (self.overflow_head is not None)

        if len(self.primary) < self.fr:
            self.primary.append(entry)
            return collision, False

        # overflow
        if self.overflow_head is None:
            self.overflow_head = OverflowPage(self.fr)

        cur = self.overflow_head
        while not cur.has_space():
            if cur.next is None:
                cur.next = OverflowPage(self.fr)
            cur = cur.next

        cur.entries.append(entry)
        return collision, True

    def find(self, key: str) -> tuple[BucketEntry | None, int]:
        """
        Retorna (entry, overflow_pages_visited)
        """
        for e in self.primary:
            if e.key == key:
                return e, 0

        visited = 0
        cur = self.overflow_head
        while cur is not None:
            visited += 1
            for e in cur.entries:
                if e.key == key:
                    return e, visited
            cur = cur.next

        return None, visited

    def overflow_page_count(self) -> int:
        c = 0
        cur = self.overflow_head
        while cur is not None:
            c += 1
            cur = cur.next
        return c

    def total_entries(self) -> int:
        total = len(self.primary)
        cur = self.overflow_head
        while cur is not None:
            total += len(cur.entries)
            cur = cur.next
        return total


# =========================
# Função hash
# =========================
class HashFunction:
    @staticmethod
    def hash_key(key: str, nb: int) -> int:
        h = 0
        for ch in key:
            h = (h * 31 + ord(ch)) % nb
        return h


# =========================
# Índice Hash Estático
# =========================
class StaticHashIndex:
    def __init__(self):
        self.nb = 0
        self.fr = 0
        self.buckets: list[Bucket] = []
        self.collisions = 0
        self.overflow_entries = 0
        self.inserted = 0

    def build(self, storage: TableStorage, fr: int, fill_factor: float = 1.2):
        if fr <= 0:
            raise ValueError("FR deve ser > 0.")
        if storage.page_count() == 0:
            raise ValueError("Não há páginas. Faça a paginação antes.")

        self.fr = fr
        self.collisions = 0
        self.overflow_entries = 0
        self.inserted = 0

        nr = storage.nr()

        # ✅ GARANTIA EXPLÍCITA DO PDF: NB > NR/FR
        min_nb = math.floor(nr / fr) + 1  # garante estritamente >
        base = max(min_nb, math.ceil((nr / fr) * fill_factor), 3)
        self.nb = next_prime(base)

        self.buckets = [Bucket(i, fr) for i in range(self.nb)]

        for page in storage.pages:
            pid = page.page_id
            for key in page.records:
                bid = HashFunction.hash_key(key, self.nb)
                col, ov = self.buckets[bid].insert(BucketEntry(key, pid))
                self.inserted += 1
                if col:
                    self.collisions += 1
                if ov:
                    self.overflow_entries += 1

    def collision_rate_pct(self) -> float:
        return (self.collisions / self.inserted * 100.0) if self.inserted else 0.0

    def overflow_rate_pct(self) -> float:
        return (self.overflow_entries / self.inserted * 100.0) if self.inserted else 0.0

    def search(self, key: str):
        """
        Retorna:
        found, bucket_id, page_id, overflow_visited, cost_pages, elapsed_ms
        custo = 1 (bucket) + overflow_pages_visited + (1 se achar e precisar ler a página)
        """
        if self.nb == 0:
            raise ValueError("Índice não construído.")

        t0 = time.perf_counter()
        bucket_id = HashFunction.hash_key(key, self.nb)
        entry, visited = self.buckets[bucket_id].find(key)

        if entry is None:
            cost = 1 + visited
            t1 = time.perf_counter()
            return False, bucket_id, -1, visited, cost, (t1 - t0) * 1000.0

        cost = 1 + visited + 1
        t1 = time.perf_counter()
        return True, bucket_id, entry.page_id, visited, cost, (t1 - t0) * 1000.0


# =========================
# App Tkinter
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Índice Hash Estático (Páginas + Buckets + Canvas)")
        self.geometry("1300x820")

        self.storage = TableStorage()
        self.index = StaticHashIndex()
        self.loaded_path: str | None = None

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Carregar TXT (1 palavra/linha)", command=self.on_load).grid(row=0, column=0, padx=5, pady=5)

        ttk.Label(top, text="Tamanho da Página (tuplas/página):").grid(row=0, column=1, padx=5, pady=5, sticky="e")
        self.var_page_size = tk.StringVar(value="200")
        ttk.Entry(top, width=10, textvariable=self.var_page_size).grid(row=0, column=2, padx=5, pady=5, sticky="w")

        ttk.Label(top, text="FR (capacidade do bucket):").grid(row=0, column=3, padx=5, pady=5, sticky="e")
        self.var_fr = tk.StringVar(value="4")
        ttk.Entry(top, width=10, textvariable=self.var_fr).grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.btn_paginate = ttk.Button(top, text="Paginar Tabela", command=self.on_paginate, state="disabled")
        self.btn_paginate.grid(row=0, column=5, padx=5, pady=5)

        self.btn_build = ttk.Button(top, text="Construir Índice", command=self.on_build, state="disabled")
        self.btn_build.grid(row=0, column=6, padx=5, pady=5)

        # Busca
        search = ttk.Frame(self, padding=(10, 0, 10, 10))
        search.pack(fill="x")

        ttk.Label(search, text="Chave de busca:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_key = tk.StringVar()
        self.ent_key = ttk.Entry(search, textvariable=self.var_key, width=55)
        self.ent_key.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.ent_key.bind("<KeyRelease>", lambda e: self._update_buttons())

        self.btn_search_index = ttk.Button(search, text="Buscar com Índice", command=self.on_search_index, state="disabled")
        self.btn_search_index.grid(row=0, column=2, padx=5, pady=5)

        # ✅ Table Scan agora depende só de ter páginas e chave
        self.btn_scan = ttk.Button(search, text="Table Scan", command=self.on_table_scan, state="disabled")
        self.btn_scan.grid(row=0, column=3, padx=5, pady=5)

        search.columnconfigure(1, weight=1)

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(main, padding=10)
        right = ttk.Frame(main, padding=10)
        main.add(left, weight=1)
        main.add(right, weight=1)

        # Páginas
        ttk.Label(left, text="Primeira Página (P0)").pack(anchor="w")
        self.txt_first = tk.Text(left, height=13, wrap="none")
        self.txt_first.pack(fill="both", expand=False, pady=(0, 10))

        ttk.Label(left, text="Última Página").pack(anchor="w")
        self.txt_last = tk.Text(left, height=13, wrap="none")
        self.txt_last.pack(fill="both", expand=False, pady=(0, 10))

        ttk.Label(left, text="Saída / Log").pack(anchor="w")
        self.txt_log = tk.Text(left, height=18, wrap="none")
        self.txt_log.pack(fill="both", expand=True)

        # Estatísticas
        stats = ttk.LabelFrame(right, text="Estatísticas", padding=10)
        stats.pack(fill="x", pady=(0, 10))

        self.var_nr = tk.StringVar(value="-")
        self.var_pages = tk.StringVar(value="-")
        self.var_nb = tk.StringVar(value="-")
        self.var_coll = tk.StringVar(value="-")
        self.var_ov = tk.StringVar(value="-")

        def stat_row(r, label, var):
            ttk.Label(stats, text=label).grid(row=r, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(stats, textvariable=var).grid(row=r, column=1, sticky="w", padx=5, pady=2)

        stat_row(0, "NR (tuplas):", self.var_nr)
        stat_row(1, "Qtd. páginas:", self.var_pages)
        stat_row(2, "NB (buckets):", self.var_nb)
        stat_row(3, "Colisões (%):", self.var_coll)
        stat_row(4, "Overflows (%):", self.var_ov)

        # Canvas (mais visual)
        canvas_box = ttk.LabelFrame(right, text="Visualização (Canvas)", padding=10)
        canvas_box.pack(fill="x", pady=(0, 10))

        self.canvas = tk.Canvas(canvas_box, height=130)
        self.canvas.pack(fill="x")

        # Buckets
        buckets_box = ttk.LabelFrame(right, text="Buckets (resumo + detalhe)", padding=10)
        buckets_box.pack(fill="both", expand=True)

        top_b = ttk.Frame(buckets_box)
        top_b.pack(fill="both", expand=True)

        self.lst_buckets = tk.Listbox(top_b, height=14)
        self.lst_buckets.pack(side="left", fill="both", expand=False)
        self.lst_buckets.bind("<<ListboxSelect>>", self.on_bucket_select)

        self.txt_bucket_detail = tk.Text(top_b, wrap="none")
        self.txt_bucket_detail.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # status
        self.var_status = tk.StringVar(value="Carregue o arquivo para começar.")
        ttk.Label(self, textvariable=self.var_status, relief="sunken", anchor="w", padding=6).pack(fill="x")

    # ---------- helpers ----------
    def log(self, msg: str = ""):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def clear_log(self):
        self.txt_log.delete("1.0", "end")

    def _update_buttons(self):
        key_ok = bool(self.var_key.get().strip())
        has_pages = self.storage.page_count() > 0
        has_index = self.index.nb > 0

        self.btn_scan.config(state="normal" if (key_ok and has_pages) else "disabled")
        self.btn_search_index.config(state="normal" if (key_ok and has_index) else "disabled")

    def _render_pages_preview(self, max_lines: int = 200):
        self.txt_first.delete("1.0", "end")
        self.txt_last.delete("1.0", "end")

        if self.storage.page_count() == 0:
            self.txt_first.insert("end", "(sem páginas)\n")
            self.txt_last.insert("end", "(sem páginas)\n")
            return

        first = self.storage.pages[0]
        last = self.storage.pages[-1]

        def render(p: Page) -> str:
            out = [f"Página P{p.page_id}", f"Registros: {len(p.records)}", ""]
            for i, rec in enumerate(p.records):
                if i >= max_lines:
                    out.append(f"... (mostrando só {max_lines} linhas)")
                    break
                out.append(rec)
            return "\n".join(out) + "\n"

        self.txt_first.insert("end", render(first))
        self.txt_last.insert("end", render(last))

    def _populate_bucket_list(self):
        self.lst_buckets.delete(0, "end")
        show = min(self.index.nb, 250)
        for i in range(show):
            b = self.index.buckets[i]
            self.lst_buckets.insert("end", f"B{i} | entries={b.total_entries()} | overflowPages={b.overflow_page_count()}")
        if self.index.nb > show:
            self.lst_buckets.insert("end", f"... (mostrando {show} de {self.index.nb} buckets)")

        self.txt_bucket_detail.delete("1.0", "end")
        self.txt_bucket_detail.insert("end", "Selecione um bucket para ver detalhes.\n")

    def _draw_canvas(self, highlight_bucket: int | None = None, highlight_page: int | None = None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        if w <= 10:
            w = 1200

        # barra de páginas (visual simples)
        pages = self.storage.page_count()
        nb = self.index.nb

        self.canvas.create_text(10, 10, anchor="nw", text=f"Páginas: {pages} | Buckets: {nb}")

        # Páginas (barra)
        x0, y0 = 10, 40
        bar_w, bar_h = w - 20, 18
        self.canvas.create_rectangle(x0, y0, x0 + bar_w, y0 + bar_h)

        if pages > 0 and highlight_page is not None and highlight_page >= 0:
            px = x0 + (highlight_page / max(pages - 1, 1)) * bar_w
            self.canvas.create_line(px, y0, px, y0 + bar_h, width=3)
            self.canvas.create_text(px, y0 + bar_h + 2, anchor="n", text=f"P{highlight_page}")

        # Buckets (grade)
        gx0, gy0 = 10, 75
        cols = 40
        cell = max(8, int((w - 20) / cols))
        rows = 4
        shown = cols * rows

        self.canvas.create_text(gx0, gy0 - 15, anchor="nw", text=f"Buckets (amostra {shown})")

        for i in range(shown):
            r = i // cols
            c = i % cols
            x = gx0 + c * cell
            y = gy0 + r * cell
            self.canvas.create_rectangle(x, y, x + cell, y + cell)

        # destaque do bucket (só se estiver dentro da amostra)
        if nb > 0 and highlight_bucket is not None and 0 <= highlight_bucket < shown:
            r = highlight_bucket // cols
            c = highlight_bucket % cols
            x = gx0 + c * cell
            y = gy0 + r * cell
            self.canvas.create_rectangle(x, y, x + cell, y + cell, width=3)
            self.canvas.create_text(x, y + cell + 2, anchor="nw", text=f"B{highlight_bucket}")

    # ---------- actions ----------
    def on_load(self):
        path = filedialog.askopenfilename(
            title="Selecione o TXT (1 palavra por linha)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.loaded_path = path
            self.var_status.set("Carregando arquivo...")
            self.update_idletasks()

            nr = self.storage.load_file(path)
            self.var_nr.set(str(nr))

            # agora habilita paginação
            self.btn_paginate.config(state="normal")
            self.btn_build.config(state="disabled")

            self.clear_log()
            self.log(f"Arquivo carregado: {path}")
            self.log(f"NR (tuplas/palavras) = {nr}")

            self.var_status.set("Arquivo carregado. Clique em 'Paginar Tabela'.")
            self._draw_canvas()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar:\n{e}")
            self.var_status.set("Erro ao carregar.")

    def on_paginate(self):
        try:
            page_size = int(self.var_page_size.get().strip())
            pc = self.storage.paginate(page_size)
            self.var_pages.set(str(pc))

            self._render_pages_preview(max_lines=250)

            # depois de paginar, já libera table scan (se tiver chave)
            self.btn_build.config(state="normal")
            self._update_buttons()
            self._draw_canvas()

            self.log("")
            self.log("=== PAGINAÇÃO FEITA ===")
            self.log(f"PageSize = {page_size}")
            self.log(f"Qtd páginas = {pc}")

            self.var_status.set("Tabela paginada. Agora pode construir o índice (opcional) e buscar.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na paginação:\n{e}")

    def on_build(self):
        try:
            fr = int(self.var_fr.get().strip())
            if fr <= 0:
                raise ValueError("FR deve ser > 0.")
            if self.storage.page_count() == 0:
                raise ValueError("Pagine a tabela antes.")

            self.var_status.set("Construindo índice...")
            self.update_idletasks()

            t0 = time.perf_counter()
            self.index.build(self.storage, fr=fr, fill_factor=1.2)
            t1 = time.perf_counter()

            self.var_nb.set(str(self.index.nb))
            self.var_coll.set(f"{self.index.collision_rate_pct():.2f}")
            self.var_ov.set(f"{self.index.overflow_rate_pct():.2f}")

            self._populate_bucket_list()
            self._update_buttons()
            self._draw_canvas()

            # log e garantia NB > NR/FR (boa pra apresentação)
            nr = self.storage.nr()
            min_needed = (nr / fr)
            self.log("")
            self.log("=== ÍNDICE CONSTRUÍDO ===")
            self.log(f"FR={fr}")
            self.log(f"NB = {self.index.nb}")
            self.log(f"Regra do PDF: NB > NR/FR  =>  {self.index.nb} > {min_needed:.2f}  (OK)")
            self.log(f"Colisões = {self.index.collision_rate_pct():.2f}%")
            self.log(f"Overflows = {self.index.overflow_rate_pct():.2f}%")
            self.log(f"Tempo construção: {(t1 - t0) * 1000.0:.2f} ms")

            self.var_status.set("Índice pronto.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao construir índice:\n{e}")

    def on_search_index(self):
        key = self.var_key.get().strip()
        if not key:
            return
        try:
            found, bid, pid, ov, cost, ms = self.index.search(key)

            self.log("")
            self.log("=== BUSCA COM ÍNDICE ===")
            self.log(f"Chave: {key}")
            self.log(f"Bucket: B{bid}")
            self.log(f"Overflow pages visitadas: {ov}")
            self.log(f"Custo estimado (leituras de páginas): {cost}")
            self.log(f"Tempo: {ms:.3f} ms")

            if found:
                p = self.storage.get_page(pid)
                self.log(f"ENCONTRADO em Página: P{pid}")
                self.log(f"Confirmação (registro está na página): {key in p.records}")
            else:
                self.log("NÃO ENCONTRADO no índice.")

            self._draw_canvas(highlight_bucket=bid if bid < 160 else None,
                              highlight_page=pid if found else None)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca:\n{e}")

    def on_table_scan(self):
        key = self.var_key.get().strip()
        if not key:
            return
        try:
            found, pid, pages_read, ms, scan_log = self.storage.table_scan(key, max_log_lines=2500)

            self.log("")
            self.log("=== TABLE SCAN ===")
            self.log(f"Chave: {key}")
            self.log(f"Custo (páginas lidas): {pages_read}")
            self.log(f"Tempo: {ms:.3f} ms")
            self.log(f"Resultado: {'ENCONTRADO em P'+str(pid) if found else 'NÃO ENCONTRADO'}")
            self.log("")
            self.log("Log do scan (parcial):")
            for line in scan_log[:2000]:
                self.log(line)
            if len(scan_log) > 2000:
                self.log("... (log cortado)")

            # se já tiver índice, compara tempos
            if self.index.nb > 0:
                i_found, bid, i_pid, ov, cost, i_ms = self.index.search(key)
                self.log("")
                self.log("=== DIFERENÇA DE TEMPO ===")
                self.log(f"Índice: {i_ms:.3f} ms")
                self.log(f"Scan:   {ms:.3f} ms")
                self.log(f"Δ (scan - índice): {(ms - i_ms):.3f} ms")

                self._draw_canvas(highlight_bucket=bid if bid < 160 else None,
                                  highlight_page=pid if found else None)
            else:
                self._draw_canvas(highlight_page=pid if found else None)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha no table scan:\n{e}")

    def on_bucket_select(self, _evt=None):
        sel = self.lst_buckets.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.index.buckets):
            return

        b = self.index.buckets[idx]
        out = []
        out.append(f"Bucket B{b.bucket_id}")
        out.append(f"FR={b.fr}")
        out.append(f"Primary entries ({len(b.primary)}):")
        for e in b.primary[:200]:
            out.append(f"  {e.key} -> P{e.page_id}")
        if len(b.primary) > 200:
            out.append("  ... (cortado)")

        cur = b.overflow_head
        level = 1
        while cur is not None:
            out.append("")
            out.append(f"OverflowPage #{level} (entries={len(cur.entries)}):")
            for e in cur.entries[:200]:
                out.append(f"  {e.key} -> P{e.page_id}")
            if len(cur.entries) > 200:
                out.append("  ... (cortado)")
            cur = cur.next
            level += 1

        self.txt_bucket_detail.delete("1.0", "end")
        self.txt_bucket_detail.insert("end", "\n".join(out) + "\n")

        self._draw_canvas(highlight_bucket=b.bucket_id if b.bucket_id < 160 else None)


if __name__ == "__main__":
    App().mainloop()