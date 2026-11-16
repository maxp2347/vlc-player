"""Test GUI : ouvre l'app et chaque dialogue séquentiellement.

Usage local (nécessite un écran, Tk et VLC installés) :
    python3 tests/smoke_gui.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


def run():
    app = main.VideoPlayer()
    steps = [
        ("fenêtre principale", lambda: None),
        ("dialogue projet", app.open_start_dialog),
        ("gestionnaire de médias", app.open_media_manager),
        ("générateur de mires", app.open_mires),
        ("panneau réglages", app.open_settings),
    ]

    def step(i):
        if i >= len(steps):
            app.on_close()
            return
        name, action = steps[i]
        try:
            action()
            print(f"OK    {name}")
        except Exception as err:
            print(f"ÉCHEC {name}: {err}")
        for child in app.winfo_children():
            if isinstance(child, main.tk.Toplevel):
                child.destroy()
        app.after(400, lambda: step(i + 1))

    app.after(300, lambda: step(0))
    app.mainloop()
    print("Test GUI terminé.")


if __name__ == "__main__":
    run()
