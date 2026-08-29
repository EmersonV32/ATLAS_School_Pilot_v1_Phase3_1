# ATLAS EV3 controller

Upload `ev3_motors.py` to the EV3 with the Pybricks VS Code extension and run
only that file on the brick. The physical motor mapping is:

- Port A: Starry Night (`slot_1`)
- Port B: Mona Lisa (`slot_2`)
- Port C: Mask of Tutankhamun (`slot_3`)

At startup all artworks move up. `raise:slot_N` keeps the selected artwork up
and lowers the other two. `raise_all` restores the neutral state. If motor
geometry is reversed on a rebuilt stand, swap `UP_ANGLE` and `DOWN_ANGLE`
instead of changing the Jetson code.
