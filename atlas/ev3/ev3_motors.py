#!/usr/bin/env pybricks-micropython
"""ATLAS EV3 painting controller (upload and run on the EV3 brick)."""

from pybricks.ev3devices import Motor
from pybricks.hubs import EV3Brick
from pybricks.messaging import BluetoothMailboxServer, TextMailbox
from pybricks.parameters import Color, Port, Stop
from pybricks.tools import wait

# Physical mapping confirmed during nationals.
PICTURE_TO_PORT = {
    "slot_1": Port.A,  # Starry Night
    "slot_2": Port.B,  # Mona Lisa
    "slot_3": Port.C,  # Mask of Tutankhamun
}

UP_ANGLE = 90
DOWN_ANGLE = 0
MOTOR_SPEED = 500

ev3 = EV3Brick()
ev3.screen.clear()
ev3.screen.print("ATLAS stands")

motors = {}
for picture, port in PICTURE_TO_PORT.items():
    try:
        motors[picture] = Motor(port)
        ev3.screen.print(picture + " OK")
    except Exception:
        ev3.screen.print(picture + " missing")


def move_targets(targets):
    for picture, motor in motors.items():
        motor.run_target(
            MOTOR_SPEED,
            targets[picture],
            then=Stop.HOLD,
            wait=False,
        )
    while any(not motor.control.done() for motor in motors.values()):
        wait(10)


def raise_picture(name):
    if name not in motors:
        return "error:unknown_picture_" + name
    move_targets(
        {
            picture: UP_ANGLE if picture == name else DOWN_ANGLE
            for picture in motors
        }
    )
    return "ok"


def raise_all():
    move_targets({picture: UP_ANGLE for picture in motors})
    return "ok"


def lower_all():
    move_targets({picture: DOWN_ANGLE for picture in motors})
    return "ok"


def set_status(colour):
    colours = {
        "green": Color.GREEN,
        "amber": Color.ORANGE,
        "red": Color.RED,
    }
    if colour == "off":
        ev3.light.off()
        return "ok"
    if colour not in colours:
        return "error:unknown_colour_" + colour
    ev3.light.on(colours[colour])
    return "ok"


# Neutral state: all three artworks visible/up.
raise_all()
ev3.screen.print("Waiting for Jetson")

server = BluetoothMailboxServer()
mailbox = TextMailbox("atlas", server)
server.wait_for_connection()
ev3.screen.print("Jetson connected")
ev3.speaker.beep()

while True:
    mailbox.wait()
    command = mailbox.read()
    if command.startswith("raise:"):
        result = raise_picture(command[6:].strip())
    elif command == "raise_all":
        result = raise_all()
    elif command == "lower_all":
        result = lower_all()
    elif command.startswith("status:"):
        result = set_status(command[7:].strip())
    elif command == "ping":
        result = "pong"
    else:
        result = "error:bad_command"
    mailbox.send(result)
