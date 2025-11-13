#!/usr/bin/env python3
import threading
import subprocess

import Quartz
import CoreFoundation

import tkinter as tk
from tkinter import ttk

# ========== AppleScript helper függvények ==========

def run_applescript(cmd: str):
    """Egyszerű helper, ami lefuttat egy AppleScript parancsot."""
    subprocess.run(["osascript", "-e", cmd])


def switch_space_left():
    # Ctrl + bal nyíl (key code 123)
    run_applescript(
        'tell application "System Events" to key code 123 using control down'
    )


def switch_space_right():
    # Ctrl + jobb nyíl (key code 124)
    run_applescript(
        'tell application "System Events" to key code 124 using control down'
    )


def show_mission_control():
    # Ctrl + fel nyíl (key code 126)
    run_applescript(
        'tell application "System Events" to key code 126 using control down'
    )


# ========== Gomb -> akció mapping (globális állapot) ==========

# Az egér debuggerből:
BUTTON_SIDE_1 = 3   # első oldalsó gomb
BUTTON_SIDE_2 = 4   # második oldalsó gomb

# Lehetséges akciók belső kulcsai
ACTION_NONE            = "none"
ACTION_SPACE_LEFT      = "space_left"
ACTION_SPACE_RIGHT     = "space_right"
ACTION_MISSION_CONTROL = "mission_control"

# Jelenlegi mapping (gomb -> akció)
# Alapértelmezés: mint a mostani CLI-s verzió
button_actions = {
    BUTTON_SIDE_1: ACTION_SPACE_LEFT,
    BUTTON_SIDE_2: ACTION_SPACE_RIGHT,
}

def perform_action(action_key: str):
    """A mappingben lévő akció végrehajtása."""
    if action_key == ACTION_SPACE_LEFT:
        switch_space_left()
    elif action_key == ACTION_SPACE_RIGHT:
        switch_space_right()
    elif action_key == ACTION_MISSION_CONTROL:
        show_mission_control()
    else:
        # ACTION_NONE vagy ismeretlen: ne tegyen semmit
        pass


# ========== Egéresemény listener (háttérszálon fut) ==========

def mouse_callback(proxy, type_, event, refcon):
    if type_ == Quartz.kCGEventOtherMouseDown:
        button = Quartz.CGEventGetIntegerValueField(
            event,
            Quartz.kCGMouseEventButtonNumber
        )

        action_key = button_actions.get(button, ACTION_NONE)

        if action_key != ACTION_NONE:
            print(f"Button {button} -> {action_key}")
            perform_action(action_key)
            # Eredeti egéreseményt elnyeljük, hogy ne legyen "Back" a böngészőben
            return None

    return event


def event_listener_loop():
    """Egéresemény figyelő loop (külön szálon fut)."""
    event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventOtherMouseDown)

    event_tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        event_mask,
        mouse_callback,
        None
    )

    if not event_tap:
        print("Nem sikerült event tap-et létrehozni. "
              "Ellenőrizd az Accessibility jogosultságot!")
        return

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)

    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopDefaultMode
    )

    Quartz.CGEventTapEnable(event_tap, True)

    print("Egéresemény-listener fut (háttérszál).")

    try:
        while True:
            CoreFoundation.CFRunLoopRunInMode(
                Quartz.kCFRunLoopDefaultMode, 0.1, True
            )
    except KeyboardInterrupt:
        print("Listener leáll.")


# ========== Tkinter GUI ==========

def create_gui():
    root = tk.Tk()
    root.title("Mouseer")

    # Letisztult, kicsi ablak
    root.geometry("420x220")
    root.resizable(False, False)

    # Leíró szöveg
    description = (
        "Mouseer : extra egérgombok macOS gesztusokra.\n"
        "Készítette: Gombos Adrián\n\n"
        "Válaszd ki, melyik oldalsó gomb milyen műveletet indítson."
    )
    label = tk.Label(root, text=description, justify="left")
    label.pack(padx=16, pady=(16, 8), anchor="w")

    # Akciók, amiket a legördülőben mutatunk
    ACTION_LABELS = {
        "Nincs akció": ACTION_NONE,
        "Space balra": ACTION_SPACE_LEFT,
        "Space jobbra": ACTION_SPACE_RIGHT,
        "Mission Control": ACTION_MISSION_CONTROL,
    }

    # Fordított mapping, hogy a belső kulcsból labelt kapjunk
    REVERSE_LABELS = {v: k for k, v in ACTION_LABELS.items()}

    # ----- Side button 1 (button 3) -----
    frame1 = tk.Frame(root)
    frame1.pack(fill="x", padx=16, pady=4)

    tk.Label(frame1, text=f"Side button 1 (button={BUTTON_SIDE_1}):").pack(
        side="left"
    )

    var_btn1 = tk.StringVar(
        value=REVERSE_LABELS.get(button_actions[BUTTON_SIDE_1], "Space balra")
    )

    combo1 = ttk.Combobox(
        frame1,
        textvariable=var_btn1,
        values=list(ACTION_LABELS.keys()),
        state="readonly",
        width=20,
    )
    combo1.pack(side="right")

    # ----- Side button 2 (button 4) -----
    frame2 = tk.Frame(root)
    frame2.pack(fill="x", padx=16, pady=4)

    tk.Label(frame2, text=f"Side button 2 (button={BUTTON_SIDE_2}):").pack(
        side="left"
    )

    var_btn2 = tk.StringVar(
        value=REVERSE_LABELS.get(button_actions[BUTTON_SIDE_2], "Space jobbra")
    )

    combo2 = ttk.Combobox(
        frame2,
        textvariable=var_btn2,
        values=list(ACTION_LABELS.keys()),
        state="readonly",
        width=20,
    )
    combo2.pack(side="right")

    # Mentés / Apply gomb (igazából azonnal érvényesítjük, de jó UX-nek)
    def apply_changes():
        button_actions[BUTTON_SIDE_1] = ACTION_LABELS[var_btn1.get()]
        button_actions[BUTTON_SIDE_2] = ACTION_LABELS[var_btn2.get()]
        print("Új mapping:", button_actions)

    apply_btn = ttk.Button(root, text="Beállítások alkalmazása", command=apply_changes)
    apply_btn.pack(pady=(12, 8))

    # Ablak bezárásakor ne szálljon el az app, csak "tálcára kerüljön"
    def on_close():
        # egyszerű verzió: minimalizáljuk az ablakot
        root.iconify()
        # ha teljesen el szeretnéd rejteni:
        # root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_close)

    return root


# ========== main ==========

def main():
    # Háttérszálon indítjuk a listener loopot
    listener_thread = threading.Thread(
        target=event_listener_loop,
        daemon=True,
    )
    listener_thread.start()

    # GUI a főszálon
    root = create_gui()
    print("ℹ Mouse Mapper GUI fut. Minimalizáld az ablakot, a háttérben tovább fut.")
    root.mainloop()


if __name__ == "__main__":
    main()