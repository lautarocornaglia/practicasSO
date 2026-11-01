from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(25)

    ## para el Gantt (opcional)
    # HARDWARE.cpu.enable_stats = True

    ## Cambio de scheduler "en frio": se elige uno solo, se cambia esta linea y se vuelve a correr.
    ## (el scheduler se crea despues del setup porque Round Robin necesita el timer)
    scheduler = SchedulerFCFS()
    # scheduler = SchedulerPriorityNonPreemptive()
    # scheduler = SchedulerPriorityPreemptive()
    # scheduler = SchedulerRoundRobin(4)

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(scheduler)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    ## Switch on computer
    HARDWARE.switchOn()

    # execute all programs "concurrently"
    kernel.run(prg1, 1)  ## 1 = prioridad del proceso
    kernel.run(prg2, 2)
    kernel.run(prg3, 3)
