#!/usr/bin/env python3
import Quartz
import CoreFoundation
import subprocess

# --- A debug alapján: ---
BUTTON_SIDE_1 = 3   # első oldalsó gomb
BUTTON_SIDE_2 = 4   # második oldalsó gomb

# --- AppleScript helper függvények ---

def run_applescript(cmd: str):
    """Egyszerű helper, ami lefuttat egy AppleScript-et."""
    subprocess.run(["osascript", "-e", cmd])


def switch_space_left():
    # Ctrl + bal nyíl (key code 123)
    run_applescript('tell application "System Events" to key code 123 using control down')


def switch_space_right():
    # Ctrl + jobb nyíl (key code 124)
    run_applescript('tell application "System Events" to key code 124 using control down')


def show_mission_control():
    # Ctrl + fel nyíl (key code 126)
    run_applescript('tell application "System Events" to key code 126 using control down')


# --- Egéresemény callback ---

def mouse_callback(proxy, type_, event, refcon):
    if type_ == Quartz.kCGEventOtherMouseDown:
        button = Quartz.CGEventGetIntegerValueField(
            event,
            Quartz.kCGMouseEventButtonNumber
        )

        if button == BUTTON_SIDE_1:
            print("Side button 1 (button=3) -> Space balra")
            switch_space_left()
            return None  # eredeti egérevent elnyelése

        elif button == BUTTON_SIDE_2:
            print("Side button 2 (button=4) -> Space jobbra")
            switch_space_right()
            return None

    return event


def main():
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
        print("Nem sikerült event tap-et létrehozni. Ellenőrizd az Accessibility jogosultságot!")
        return

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)

    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopDefaultMode
    )

    Quartz.CGEventTapEnable(event_tap, True)

    print("Fut az egér-mapper (AppleScript móddal).")
    print("   Side button 1 (button=3) -> Space balra")
    print("   Side button 2 (button=4) -> Space jobbra")
    print("   Ctrl+C-vel tudsz kilépni.\n")

    try:
        while True:
            CoreFoundation.CFRunLoopRunInMode(
                Quartz.kCFRunLoopDefaultMode, 0.1, True
            )
    except KeyboardInterrupt:
        print("\nKilépés (Ctrl+C).")


if __name__ == "__main__":
    main()
