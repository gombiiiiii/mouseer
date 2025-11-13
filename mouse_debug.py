#!/usr/bin/env python3
import Quartz
import CoreFoundation

def describe_event_type(type_):
    mapping = {
        Quartz.kCGEventLeftMouseDown: "LeftMouseDown",
        Quartz.kCGEventLeftMouseUp: "LeftMouseUp",
        Quartz.kCGEventRightMouseDown: "RightMouseDown",
        Quartz.kCGEventRightMouseUp: "RightMouseUp",
        Quartz.kCGEventOtherMouseDown: "OtherMouseDown",
        Quartz.kCGEventOtherMouseUp: "OtherMouseUp",
        Quartz.kCGEventScrollWheel: "ScrollWheel",
    }
    return mapping.get(type_, f"OtherType({type_})")

def mouse_callback(proxy, type_, event, refcon):
    event_name = describe_event_type(type_)

    # A legtöbb gombnál érdemes megnézni a buttonNumber-t
    button = Quartz.CGEventGetIntegerValueField(
        event,
        Quartz.kCGMouseEventButtonNumber
    )

    # Scrollnál a delta érték is érdekes lehet
    if type_ == Quartz.kCGEventScrollWheel:
        delta_y = Quartz.CGEventGetIntegerValueField(
            event,
            Quartz.kCGScrollWheelEventDeltaAxis1
        )
        print(f"[{event_name}] delta_y={delta_y}")
    else:
        print(f"[{event_name}] button={button}")

    return event

def main():
    # Figyeljük:
    # - left/right/other mouse down
    # - scroll wheel
    event_mask = (
        Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown) |
        Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDown) |
        Quartz.CGEventMaskBit(Quartz.kCGEventOtherMouseDown) |
        Quartz.CGEventMaskBit(Quartz.kCGEventScrollWheel)
    )

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

    print("Fut a listener.")
    print("   Mozgasd / kattintgasd az egeret,", 
          "kattints bal/jobb/oldalsó/görgő gombra.")
    print("   Ctrl+C-vel tudsz kilépni.\n")

    try:
        # Nem blokkoló, hogy a Ctrl+C-t elkapja a Python
        while True:
            CoreFoundation.CFRunLoopRunInMode(
                Quartz.kCFRunLoopDefaultMode, 0.1, True
            )
    except KeyboardInterrupt:
        print("\nKilépés (Ctrl+C).")

if __name__ == "__main__":
    main()
