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
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


## estados posibles de un proceso
STATE_NEW = "new"
STATE_READY = "ready"
STATE_RUNNING = "running"
STATE_WAITING = "waiting"
STATE_TERMINATED = "terminated"


## Process Control Block: la ficha de cada proceso
class PCB():

    def __init__(self, pid, baseDir, path):
        self._pid = pid
        self._baseDir = baseDir
        self._pc = 0
        self._state = STATE_NEW
        self._path = path

    @property
    def pid(self):
        return self._pid

    @property
    def baseDir(self):
        return self._baseDir

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, pc):
        self._pc = pc

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def path(self):
        return self._path

    def __repr__(self):
        return "PCB(pid={pid}, path={path}, baseDir={base}, pc={pc}, state={state})".format(
            pid=self._pid, path=self._path, base=self._baseDir, pc=self._pc, state=self._state)


## tabla con todos los PCB del sistema
class PCBTable():

    def __init__(self):
        self._table = {}
        self._nextPid = 0

    def get(self, pid):
        return self._table[pid]

    def add(self, pcb):
        self._table[pcb.pid] = pcb

    def remove(self, pid):
        del self._table[pid]

    def getNewPID(self):
        # los pid no se reutilizan, siempre sube
        pid = self._nextPid
        self._nextPid += 1
        return pid

    def __repr__(self):
        return "PCBTable({t})".format(t=list(self._table.values()))


## cola de procesos listos para correr (fifo)
class ReadyQueue():

    def __init__(self):
        self._queue = []

    def add(self, pcb):
        self._queue.append(pcb)

    def next(self):
        # saca el primero de la cola
        return self._queue.pop(0)

    def isEmpty(self):
        return len(self._queue) == 0

    def __repr__(self):
        return "ReadyQueue({q})".format(q=self._queue)


## carga los programas en memoria
class Loader():

    def __init__(self):
        # proxima celda libre de la memoria
        self._nextDir = 0

    def load(self, program):
        baseDir = self._nextDir
        for index in range(0, len(program.instructions)):
            HARDWARE.memory.write(baseDir + index, program.instructions[index])
        self._nextDir = baseDir + len(program.instructions)
        return baseDir


## pone y saca procesos de la cpu (cambio de contexto)
class Dispatcher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir

    def save(self, pcb):
        # guardo el pc en el pcb y dejo la cpu idle
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1


## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


## TODO: los 4 handlers quedan para el companiero

class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        program = irq.parameters

        # Cargamos el programa en memoria
        baseDir = self.kernel.loader.load(program)

        # Creamos el PCB y lo agregamos a la tabla
        pid = self.kernel.pcbTable.getNewPID()
        pcb = PCB(pid, baseDir, program.name)
        self.kernel.pcbTable.add(pcb)

        # Si la CPU está libre, ejecutamos el proceso
        if self.kernel.runningPCB is None:
            self.kernel.dispatcher.load(pcb)
            pcb.state = STATE_RUNNING
            self.kernel.runningPCB = pcb
        else:
            # Si está ocupada, lo agregamos a Ready
            pcb.state = STATE_READY
            self.kernel.readyQueue.add(pcb)

        log.logger.info("NEW: {}".format(pcb))


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.runningPCB

        # Finalizamos el proceso actual
        self.kernel.dispatcher.save(pcb)
        pcb.state = STATE_TERMINATED

        # Lo eliminamos de la tabla
        self.kernel.pcbTable.remove(pcb.pid)
        self.kernel.runningPCB = None

        log.logger.info("KILL: {}".format(pcb))

        # Buscamos otro proceso para ejecutar
        if not self.kernel.readyQueue.isEmpty():
            nextPCB = self.kernel.readyQueue.next()
            self.kernel.dispatcher.load(nextPCB)
            nextPCB.state = STATE_RUNNING
            self.kernel.runningPCB = nextPCB


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.runningPCB

        # Guardamos el estado del proceso actual
        self.kernel.dispatcher.save(pcb)
        pcb.state = STATE_WAITING
        self.kernel.runningPCB = None

        # Enviamos la operación al dispositivo de I/O
        self.kernel.ioDeviceController.runOperation(
            pcb, irq.parameters
        )

        log.logger.info("IO_IN: {}".format(pcb))

        # Ejecutamos el siguiente proceso de Ready
        if not self.kernel.readyQueue.isEmpty():
            nextPCB = self.kernel.readyQueue.next()
            self.kernel.dispatcher.load(nextPCB)
            nextPCB.state = STATE_RUNNING
            self.kernel.runningPCB = nextPCB


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # Recuperamos el proceso que terminó su I/O
        pcb = self.kernel.ioDeviceController.getFinishedPCB()

        log.logger.info("IO_OUT: {}".format(pcb))

        # Si la CPU está libre, lo ejecutamos
        if self.kernel.runningPCB is None:
            self.kernel.dispatcher.load(pcb)
            pcb.state = STATE_RUNNING
            self.kernel.runningPCB = pcb
        else:
            # Si está ocupada, pasa a Ready
            pcb.state = STATE_READY
            self.kernel.readyQueue.add(pcb)

# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        ## componentes del so
        self._loader = Loader()
        self._dispatcher = Dispatcher()
        self._pcbTable = PCBTable()
        self._readyQueue = ReadyQueue()
        self._runningPCB = None

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
    def readyQueue(self):
        return self._readyQueue

    @property
    def runningPCB(self):
        return self._runningPCB

    @runningPCB.setter
    def runningPCB(self, pcb):
        self._runningPCB = pcb

    ## emulates a "system call" for programs execution
    def run(self, program):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "