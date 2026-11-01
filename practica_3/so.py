#!/usr/bin/env python

from hardware import *
import log


## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        self._waiting_queue.append(pair)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            pair = self._waiting_queue.pop(0)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(
            deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


## estados de un proceso
STATE_NEW = "new"
STATE_READY = "ready"
STATE_RUNNING = "running"
STATE_WAITING = "waiting"
STATE_TERMINATED = "terminated"


class PCB():

    def __init__(self, pid, baseDir, limit, path, priority):
        self._pid = pid
        self._baseDir = baseDir
        self._limit = limit
        self._pc = 0
        self._state = STATE_NEW
        self._path = path
        self._priority = priority          # la que se usa para ordenar (el aging la va cambiando)
        self._basePriority = priority      # la original, por si hay que volver a ella

    @property
    def pid(self):
        return self._pid

    @property
    def baseDir(self):
        return self._baseDir

    @property
    def limit(self):
        return self._limit

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value):
        self._pc = value

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def path(self):
        return self._path

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, value):
        self._priority = value

    @property
    def basePriority(self):
        return self._basePriority

    def __repr__(self):
        return "PCB(pid={pid}, state={state}, pc={pc}, prio={prio})".format(
            pid=self._pid, state=self._state, pc=self._pc, prio=self._priority)


class PCBTable():

    def __init__(self):
        self._table = {}
        self._nextPid = 0

    def newPid(self):
        pid = self._nextPid
        self._nextPid += 1
        return pid

    def add(self, pcb):
        self._table[pcb.pid] = pcb

    def get(self, pid):
        return self._table[pid]

    def all(self):
        return list(self._table.values())

    def allTerminated(self):
        return all(p.state == STATE_TERMINATED for p in self._table.values())


class Loader():

    def __init__(self):
        self._nextDir = 0

    def load(self, program):
        baseDir = self._nextDir
        progSize = len(program.instructions)
        for index in range(0, progSize):
            HARDWARE.memory.write(baseDir + index, program.instructions[index])
        self._nextDir += progSize
        return baseDir


class Dispatcher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir
        HARDWARE.mmu.limit = pcb.limit
        HARDWARE.timer.reset()      # cada proceso que entra arranca con el contador del timer en 0

    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1


## ---------------------------------------------------------------
##  SCHEDULER
##  Es el unico que toca la ready queue. Los handlers solo llaman a estos metodos.
## ---------------------------------------------------------------
class Scheduler():

    def add(self, pcb):
        # TODO
        pass

    def getNext(self):
        # TODO
        pass

    def isEmpty(self):
        # TODO
        pass

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        # TODO (por defecto tiene que dar False)
        pass


class SchedulerFCFS(Scheduler):
    # TODO
    pass


class SchedulerPriorityNonPreemptive(Scheduler):
    # TODO (con aging)
    pass


class SchedulerPriorityPreemptive(Scheduler):
    # TODO (con aging)
    pass


class SchedulerRoundRobin(Scheduler):
    # TODO (tiene que configurar HARDWARE.timer.quantum)
    pass


## ---------------------------------------------------------------
##  HANDLERS
## ---------------------------------------------------------------
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    # Opcional: logica que se repite en #NEW y #IO_OUT (pasar a running o a ready segun corresponda).
    # TODO si les sirve, hacerla aca.


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # parameters = irq.parameters  ->  {'program': ..., 'priority': ...}
        # TODO
        pass


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # TODO
        pass


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # TODO
        pass


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # TODO
        pass


class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # TODO
        pass


class StatInterruptionHandler(AbstractInterruptionHandler):
    # Opcional, para el Gantt. Tick actual: HARDWARE.clock.currentTick

    def execute(self, irq):
        # TODO
        pass


# emulates the core of an Operative System
class Kernel():

    def __init__(self, scheduler):
        ## setup interruption handlers
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, NewInterruptionHandler(self))
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, KillInterruptionHandler(self))
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, IoInInterruptionHandler(self))
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, IoOutInterruptionHandler(self))
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, TimeOutInterruptionHandler(self))
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, StatInterruptionHandler(self))

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        self._loader = Loader()
        self._dispatcher = Dispatcher()
        self._pcbTable = PCBTable()
        self._scheduler = scheduler
        self._runningPCB = None        # None = CPU libre

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def loader(self):
        return self._loader

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def pcbTable(self):
        return self._pcbTable

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def runningPCB(self):
        return self._runningPCB

    @runningPCB.setter
    def runningPCB(self, pcb):
        self._runningPCB = pcb

    ## emulates a "system call" for programs execution
    def run(self, program, priority):
        parameters = {'program': program, 'priority': priority}
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, parameters)
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "
