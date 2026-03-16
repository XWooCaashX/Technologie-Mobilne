import tkinter as tk
from tkinter import ttk
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stacja Bazowa - Symulator")
        self.geometry("1400x800")
        
        # Zmienne kontrolne symulacji
        self.is_running = False
        self.current_time = 0
        self.calls = []          # Lista oczekujących wygenerowanych zgłoszeń
        self.channels = []       # Czas pozostały dla poszczególnych kanałów
        self.queue = []          # Zgłoszenia w kolejce (śledzenie czasu oczekiwania)
        self.handled_calls = 0
        self.rejected_calls = 0
        
        # Zmienne do wykresów
        self.history_q = []
        self.history_w = []
        self.history_ro = []
        self.history_t = []

        self.setup_ui()

    def setup_ui(self):
        # Główny podział okna na 3 panele (Lewy - Parametry, Środek - Wizualizacja, Prawy - Wykresy)
        left_frame = tk.Frame(self, width=300, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        center_frame = tk.Frame(self, width=300, padx=10, pady=10)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        
        right_frame = tk.Frame(self, padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- PANEL LEWY: Parametry ---
        tk.Label(left_frame, text="Parametry", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        params = [
            ("Liczba kanałów", "10"),
            ("Długość kolejki", "10"),
            ("Natężenie ruchu [lambda]", "1.0"),
            ("Średnia dług. rozmowy [s]", "20"),
            ("Odchylenie standardowe", "5"),
            ("Minimalny czas połącz. [s]", "10"),
            ("Maksymalny czas połącz. [s]", "30"),
            ("Czas symulacji [s]", "30")
        ]
        
        self.entries = {}
        for i, (label_text, default_val) in enumerate(params):
            tk.Label(left_frame, text=label_text).grid(row=i+1, column=0, sticky="w")
            entry = tk.Entry(left_frame, width=10)
            entry.insert(0, default_val)
            entry.grid(row=i+1, column=1, pady=2)
            self.entries[label_text] = entry

        # Przyciski sterujące
        btn_frame = tk.Frame(left_frame)
        btn_frame.grid(row=len(params)+1, column=0, columnspan=2, pady=20)
        tk.Button(btn_frame, text="START", font=("Arial", 12, "bold"), width=10, command=self.start_simulation).grid(row=0, column=0, rowspan=2, padx=5)
        
        # Tabela wyników szczegółowych (uproszczona)
        columns = ("Pois", "Gauss", "T_Przy", "T_Obs")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=60)
        self.tree.grid(row=len(params)+2, column=0, columnspan=2, pady=10)

        # --- PANEL ŚRODKOWY: Wizualizacja ---
        tk.Label(center_frame, text="Kanały", font=("Arial", 14, "bold")).pack(pady=10)
        self.channels_frame = tk.Frame(center_frame)
        self.channels_frame.pack()
        self.channel_labels = [] # Zostaną wypełnione w start_simulation
        
        tk.Label(center_frame, text="Kolejka").pack(pady=(20, 0))
        self.queue_bar = ttk.Progressbar(center_frame, orient="horizontal", length=200, mode="determinate")
        self.queue_bar.pack(pady=5)
        self.queue_lbl = tk.Label(center_frame, text="Kolejka: 0 / 10")
        self.queue_lbl.pack()
        
        self.stats_lbl = tk.Label(center_frame, text="Obsłużone połączenia: 0\nLicznik odrzuconych: 0")
        self.stats_lbl.pack(pady=20)
        self.time_lbl = tk.Label(center_frame, text="Czas symulacji: 0 / 30", font=("Arial", 12, "bold"))
        self.time_lbl.pack(pady=10)

        # --- PANEL PRAWY: Wykresy ---
        self.fig, (self.ax_q, self.ax_w, self.ax_ro) = plt.subplots(3, 1, figsize=(6, 8))
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def get_param(self, name, param_type=float):
        return param_type(self.entries[name].get())

    def start_simulation(self):
        self.is_running = False
        
        # Pobranie parametrów
        self.num_channels = self.get_param("Liczba kanałów", int)
        self.max_queue = self.get_param("Długość kolejki", int)
        self.lam = self.get_param("Natężenie ruchu [lambda]")
        self.n_mean = self.get_param("Średnia dług. rozmowy [s]")
        self.sigma = self.get_param("Odchylenie standardowe")
        self.t_min = self.get_param("Minimalny czas połącz. [s]")
        self.t_max = self.get_param("Maksymalny czas połącz. [s]")
        self.sim_time = self.get_param("Czas symulacji [s]", int)

        # Inicjalizacja stanu
        self.current_time = 0
        self.handled_calls = 0
        self.rejected_calls = 0
        self.channels = [0] * self.num_channels
        self.queue = []
        
        self.history_q.clear()
        self.history_w.clear()
        self.history_ro.clear()
        self.history_t.clear()
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Rysowanie interfejsu kanałów
        for widget in self.channels_frame.winfo_children():
            widget.destroy()
        self.channel_labels = []
        for i in range(self.num_channels):
            lbl = tk.Label(self.channels_frame, text="0", width=5, height=2, bg="green", fg="white", font=("Arial", 12, "bold"))
            lbl.grid(row=i//2, column=i%2, padx=5, pady=5)
            self.channel_labels.append(lbl)

        # Krok 1 i 2: Generowanie listy zgłoszeń
        self.calls = []
        t = 0
        while t <= self.sim_time + 10:  # Generujemy z małym zapasem
            inter_arrival = random.expovariate(self.lam) # Odpowiada procesowi Poissona dla wejść
            t += inter_arrival
            duration = random.gauss(self.n_mean, self.sigma)
            duration = max(self.t_min, min(self.t_max, duration)) # Ograniczenia
            self.calls.append({"arrival": t, "duration": int(duration)})
            
            # Dodaj do tabeli
            self.tree.insert("", "end", values=(f"{inter_arrival:.3f}", f"{duration:.2f}", f"{int(t)}", f"{int(duration)}"))

        self.queue_bar["maximum"] = self.max_queue
        self.is_running = True
        self.step_simulation() # Krok 3: rozpoczęcie pętli symulacji

    def step_simulation(self):
        if not self.is_running or self.current_time >= self.sim_time:
            self.is_running = False
            return

        self.current_time += 1 # 1 krok = 1 sekunda

        # A: Zmniejszanie czasu połączeń w kanałach i uwalnianie kanałów
        for i in range(self.num_channels):
            if self.channels[i] > 0:
                self.channels[i] -= 1

        # B: Obsługa kolejki (dodanie do czasu oczekiwania)
        for q_item in self.queue:
            q_item['wait_time'] += 1

        # C: Pobranie nowych zgłoszeń z aktualnej sekundy
        incoming_calls = [c for c in self.calls if self.current_time - 1 < c["arrival"] <= self.current_time]

        # Umieszczanie nowych zgłoszeń w kanałach lub kolejce
        for call in incoming_calls:
            placed = False
            # Szukaj wolnego kanału
            for i in range(self.num_channels):
                if self.channels[i] == 0:
                    self.channels[i] = call["duration"]
                    placed = True
                    self.handled_calls += 1
                    break
            
            # Brak wolnego kanału -> do kolejki
            if not placed:
                if len(self.queue) < self.max_queue:
                    self.queue.append({'duration': call["duration"], 'wait_time': 0})
                else:
                    self.rejected_calls += 1

        # D: Przenoszenie z kolejki do wolnych kanałów
        for i in range(self.num_channels):
            if self.channels[i] == 0 and len(self.queue) > 0:
                q_call = self.queue.pop(0)
                self.channels[i] = q_call['duration']
                self.handled_calls += 1

        # Aktualizacja logiki i interfejsu (Obliczenia ro, Q, W)
        self.update_ui()
        self.update_plots()

        # Symulacja opóźnienia 1 sekunda (1000ms), tu skrócone do 200ms by działało dynamicznie
        self.after(200, self.step_simulation)

    def update_ui(self):
        # Aktualizacja kanałów
        for i in range(self.num_channels):
            rem_time = self.channels[i]
            if rem_time > 0:
                self.channel_labels[i].config(text=str(rem_time), bg="red")
            else:
                self.channel_labels[i].config(text="0", bg="green")
        
        # Aktualizacja kolejki i tekstów
        self.queue_bar["value"] = len(self.queue)
        self.queue_lbl.config(text=f"Kolejka: {len(self.queue)} / {self.max_queue}")
        self.stats_lbl.config(text=f"Obsłużone połączenia: {self.handled_calls}\nLicznik odrzuconych: {self.rejected_calls}")
        self.time_lbl.config(text=f"Czas symulacji: {self.current_time} / {self.sim_time}")

    def update_plots(self):
        # Statystyki do wykresów
        busy_channels = sum(1 for c in self.channels if c > 0)
        ro = busy_channels / self.num_channels if self.num_channels > 0 else 0
        q_len = len(self.queue)
        
        # Średni czas oczekiwania w danej chwili - np. ze wszystkich aktualnie w kolejce
        w_time = sum(item['wait_time'] for item in self.queue) / q_len if q_len > 0 else 0

        self.history_t.append(self.current_time)
        self.history_ro.append(ro)
        self.history_q.append(q_len)
        self.history_w.append(w_time)

        # Odświeżenie rysunków
        self.ax_q.clear()
        self.ax_w.clear()
        self.ax_ro.clear()

        self.ax_q.plot(self.history_t, self.history_q, 'r-')
        self.ax_q.set_title("Q (Kolejka)")
        self.ax_q.grid(True, linestyle='--')

        self.ax_w.plot(self.history_t, self.history_w, 'b-')
        self.ax_w.set_title("W (Czas oczek.)")
        self.ax_w.grid(True, linestyle='--')

        self.ax_ro.plot(self.history_t, self.history_ro, 'g-')
        self.ax_ro.set_title("Ro (Zajętość)")
        self.ax_ro.set_ylim(-0.1, 1.1)
        self.ax_ro.grid(True, linestyle='--')

        self.canvas.draw()

if __name__ == "__main__":
    app = SimulatorApp()
    app.mainloop()