#!/usr/bin/env python3
import threading
import subprocess
import queue

import Quartz
import CoreFoundation
from Foundation import NSAppleScript

import tkinter as tk
from tkinter import ttk


# ========== AppleScript helper függvények (NSAppleScript-tel) ==========

# Előre lefordított AppleScript objektumok – nem indul külön processz kattintásonként
_space_left_script = NSAppleScript.alloc().initWithSource_(
    'tell application "System Events" to key code 123 using control down'
)
_space_right_script = NSAppleScript.alloc().initWithSource_(
    'tell application "System Events" to key code 124 using control down'
)
_mission_control_script = NSAppleScript.alloc().initWithSource_(
    'tell application "System Events" to key code 126 using control down'
)


def switch_space_left():
    _space_left_script.executeAndReturnError_(None)


def switch_space_right():
    _space_right_script.executeAndReturnError_(None)


def show_mission_control():
    _mission_control_script.executeAndReturnError_(None)


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
# Alapértelmezés: mint a korábbi CLI-s verzió
button_actions = {
    BUTTON_SIDE_1: ACTION_SPACE_LEFT,
    BUTTON_SIDE_2: ACTION_SPACE_RIGHT,
}

def perform_action(action_key: str):
    """A mappingben lévő akció végrehajtása (ez már külön worker szálon fut)."""
    if action_key == ACTION_SPACE_LEFT:
        switch_space_left()
    elif action_key == ACTION_SPACE_RIGHT:
        switch_space_right()
    elif action_key == ACTION_MISSION_CONTROL:
        show_mission_control()
    else:
        # ACTION_NONE vagy ismeretlen: ne tegyen semmit
        pass


# ========== Queue az akcióknak + worker szál ==========

action_queue: "queue.Queue[str]" = queue.Queue()

def action_worker():
    """Külön szál, ami végrehajtja a kattintásokhoz tartozó akciókat."""
    #print("Action worker szál elindult.")
    while True:
        action_key = action_queue.get()
        try:
            perform_action(action_key)
        except Exception as e:
            print("Hiba az akció végrehajtásakor:", e)
        finally:
            action_queue.task_done()


# ========== Egéresemény listener (háttérszálon fut) ==========

event_tap = None  # globális, hogy callbackből újra tudjuk engedélyezni

def mouse_callback(proxy, type_, event, refcon):
    global event_tap

    # Ha a rendszer letiltja a tap-et timeout vagy user input miatt
    if type_ == Quartz.kCGEventTapDisabledByTimeout or \
       type_ == Quartz.kCGEventTapDisabledByUserInput:
        print("Event tap letiltva, újraengedélyezem...")
        if event_tap is not None:
            Quartz.CGEventTapEnable(event_tap, True)
        return event

    if type_ == Quartz.kCGEventOtherMouseDown:
        button = Quartz.CGEventGetIntegerValueField(
            event,
            Quartz.kCGMouseEventButtonNumber
        )

        action_key = button_actions.get(button, ACTION_NONE)

        if action_key != ACTION_NONE:
            # FONTOS: itt csak betesszük a queue-ba és AZONNAL visszatérünk,
            # hogy a callback gyors legyen → ne tiltsa le a macOS a tap-et.
            #print(f"Button {button} -> {action_key} (queued)")
            action_queue.put(action_key)
            # Eredeti egéreseményt elnyeljük, hogy ne legyen "Back" a böngészőben
            return None

    return event


def event_listener_loop():
    """Egéresemény figyelő loop (külön szálon fut)."""
    global event_tap

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

    #print("Egéresemény-listener fut (háttérszál).")

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

    # Letisztult, kicsi ablak – méret
    window_width = 420
    window_height = 220
    root.geometry(f"{window_width}x{window_height}")
    root.resizable(False, False)

    # --- Ablak középre igazítása ---
    root.update_idletasks()  # hogy legyenek érvényes méretek
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    # -------------------------------

    # Leíró szöveg
    description = (
        "Mouseer : extra egérgombok macOS gesztusokra.\n\n"
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

    # Mentés / Apply gomb
    def apply_changes():
        button_actions[BUTTON_SIDE_1] = ACTION_LABELS[var_btn1.get()]
        button_actions[BUTTON_SIDE_2] = ACTION_LABELS[var_btn2.get()]
        status_var.set("Beállítások alkalmazva")

    apply_btn = ttk.Button(root, text="Beállítások alkalmazása", command=apply_changes)
    apply_btn.pack(pady=(12, 4))

    # --- Státuszsor az ablak alján ---
    global status_var
    status_var = tk.StringVar(value="Készítette: Gombos Adrián")
    status_label = tk.Label(root, textvariable=status_var,
                            anchor="w", fg="gray")
    status_label.pack(fill="x", padx=8, pady=(0, 6), side="bottom")
    # ---------------------------------

    # Ablak bezárásakor ne szálljon el az app, csak "tálcára kerüljön"
    def on_close():
        root.iconify()
        # root.withdraw()  # ha teljesen el akarod rejteni

    root.protocol("WM_DELETE_WINDOW", on_close)

    return root


# ========== main ==========

def main():
    # Action worker szál indítása
    worker_thread = threading.Thread(
        target=action_worker,
        daemon=True,
    )
    worker_thread.start()

    # Háttérszálon indítjuk a listener loopot
    listener_thread = threading.Thread(
        target=event_listener_loop,
        daemon=True,
    )
    listener_thread.start()

    # GUI a főszálon
    root = create_gui()
    #print("Mouse Mapper GUI fut. Minimalizáld az ablakot, a háttérben tovább fut.")
    root.mainloop()


if __name__ == "__main__":
    main()
