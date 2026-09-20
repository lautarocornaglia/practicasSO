# Práctica 1
## Introducción al Simulador - Procesos, Clock e Interrupciones

## Código

- El Código del simulador es este:

  - [log.py](./log.py) Se configura un logger, un logger es una herramienta para imprimir texto en pantalla o algun "output" del sistema, como por ejemplo un archivo de texto.

  - [hardware.py](./hardware.py) Emula el Hardware en el que va a correr nuestro Sistema Operativo. Ahí está nuestro __CPU__, __Memoria__, el pseudo lenguaje __ASM__, el __Clock__ y el sistema de __Interrupciones__. El hardware es accessible desde cualquier lugar del S.O. accediendo a la constante llamada __HARDWARE__

  - [so.py](./so.py) Contiene la definicion de __Program__ y un pequeño __Kernel__ (el Kernel es la parte mas importante de un __Sistema Operativo__)

  - [main.py](./main.py) inicia nuestro emulador de __Sistema Operativo__



Para correr el emulador, debemos ejecutar indicarle a Python (versón 3) que ejecute nuestro programa:

```bash
$ python main.py
```

o sino, dependiendo de nuestro sistema operativo:

```bash
$ python3 main.py
```

------------------

## Parte 1 — Un Simulador "Extremadamente" Simplificado (sin interrupciones)

Comenzamos por modelar un __programa__. Un programa tiene un nombre y una lista de instrucciones. Las instrucciones pueden ser `CPU`, `IO` o `EXIT` dependiendo si son instrucciones de cpu o entrada/salida o la última instrucción de un programa. Para comodidad queremos poder expresar algo como:

```python
p = Program("test.exe", [ASM.CPU(3), ASM.IO(), ASM.CPU(4)])
```

Qué sería un atajo para escribir:

```python
p = Program('test.exe', ['CPU', 'CPU', 'CPU', 'IO', 'CPU', 'CPU', 'CPU', 'CPU', 'EXIT'])
```

Para que todo esté listo vamos a hacer de compilador. Si creamos un programa cuya última instrucción no es `EXIT`, nosotros la agregaremos por el usuario.

Ahora que tenemos modelado nuestro programa vamos a modelar una __Cpu__ y una __Memoria__.

La __Memoria__ puede verse como un array de N celdas donde se cargan las instrucciones de los programas (comenzando en la posición 0).

Lo único que sabe hacer una __Cpu__ es obtener una intrucción de la memoria (fetch) y ejecutarla (imprimir en pantalla por ahora).

Finalemente modelemos un pequeño __Sistema Operativo__(SO) que nos permite ejecutar programas, lo primero que hará nuestro SO será cargar el programa en memoria y luego instruir a la __Cpu__ para que empiece a ejecutar. La __Cpu__ recibe una señal "tick" para indicarle que realice un ciclo de procesamiento (fetch/decode/execute).

Cuando no hay más instrucciones para ejecutar el SO devuelve el control al usuario.

### Ejercicio Parte 1

1. Entender el código que se encuentra en [sin_interrupciones/](./sin_interrupciones/). Entender código de terceros siempre es más difícil que escribirlo, pero también se aprende mucho.

2. Una pequeña modificación. Vamos a hacer que nuestro SO reciba una lista de programas y los ejecute uno después de otro en el orden recibido.

```python
# Ahora vamos a intentar ejecutar un lote (batch) de 3 programas
###################
prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3)])
prg2 = Program("prg2.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
prg3 = Program("prg3.exe", [ASM.CPU(3)])

batch = [prg1, prg2, prg3]
# execute the program
kernel.executeBatch(batch)
```

### Por qué este enfoque no es correcto

En esta versión, el __Kernel__ maneja la ejecución de los programas con un loop `for` manual, enviando ticks a la __CPU__ uno por uno. Esto tiene un problema fundamental: **el Sistema Operativo no se "entera" de cuándo un programa termina**. Simplemente asume que la cantidad de ticks es igual a la cantidad de instrucciones, y cuando el loop termina, pasa al siguiente programa.

En un sistema real, el hardware necesita poder "comunicarse" con el S.O. para avisarle que algo ocurrió (un programa terminó, llegó un dato de I/O, etc.). Para eso existen las __interrupciones__.


------------------

## Parte 2 — Clock e Interrupciones

En esta versión del simulador, avanzamos con un __Hardware__ "un poco" mas realista. Ahora el hardware tiene un par de metodos para "prender" y "apagar" el __Hardware__.
Mientras el __Hardware__ esté encendido, el __Clock__ envía constantemente una señal a los distintos componentes para sincronizar los ciclos de ejecución. Este ciclo se repite indefinidamente hasta apagar el hardware ("loop infinito")

```python
## prende la "maquina"
HARDWARE.switchOn()

## apaga la "maquina"
HARDWARE.switchOff()
```

Hasta acá vimos que el Software se puede "comunicar" con el Hardware (ya que para eso fue creado). Ahora vamos a ver como hace el Hardware para "comunicarse" con el S.O.

El hardware contiene un vector de interrupciones __Interrupt Vector Table__, en el mismo se registran la direcciones de las rutinas (de software) a ser ejecutadas cuando una __Interrupción__ es solicitada.

  ej:
```
  [#IRQ_1, 0001000] --> dir del interrupt hanlder de #IRQ_1
  [#IRQ_2, 0010111] --> dir del interrupt hanlder de #IRQ_2
  [#IRQ_3, 1111000] --> dir del interrupt hanlder de #IRQ_3
```

Los handlers de interrupciones son parte del S.O., El __S.O.__ es el encargado de completar el __Interrupt Vector Table__ para "escuchar" al __Hardware__.

### El simulador con interrupciones

Ahora, que nuestro __Clock__ va a estar enviando "ticks" constantemente a la __CPU__ (no vamos a poder controlar cuandos ciclos correr antes de terminar), debemos resolverlo a nivel del __Software__.

Cuando el __CPU__ detecta que el programa terminó (instrucción 'EXIT'), envia una solicitud de interrupción __IRQ__ ( o __Interruption Request__) de __#Kill__

```python
def _execute(self):
    if ASM.isEXIT(self._ir):
        killIRQ = IRQ(KILL_INTERRUPTION_TYPE)
        self._interruptVector.handle(killIRQ)
    else:
        log.logger.info("cpu - Exec: {instr}, PC={pc}".format(instr=self._ir, pc=self._pc))
```


En nuestro S.O. tenemos que configurar el __Interrupt Vector Table__ para "handlear" la interrupcion de __#Kill__

```python
## setup interruption handlers
killHandler = KillInterruptionHandler(self)
HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)
```

Cuando una iterrupcion es "lanzada", el __Interrupt Vector Table__ llama al "handler" configurado para que la "maneje", en este caso, se llamará al método __execute()__ de la clase __KillInterruptionHandler__:

```python
class KillInterruptionHandler(AbstractInterruptionHandler):
    def execute(self, irq):
        log.logger.info(" Program Finished ")
        HARDWARE.switchOff()
```

### Ejercicios Parte 2

1. Entender las clases __InterruptVector()__ y __Clock()__ y poder explicar como funcionan

2. Explicar cómo se llega a ejecutar __KillInterruptionHandler.execute()__

3. Una pequeña modificación. Vamos a hacer que nuestro SO reciba una lista de programas y los ejecute uno después de otro en el orden recibido.

```python
# Ahora vamos a intentar ejecutar un lote (batch) de 3 programas
###################
prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3)])
prg2 = Program("prg2.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
prg3 = Program("prg3.exe", [ASM.CPU(3)])

batch = [prg1, prg2, prg3]
# execute the program
kernel.executeBatch(batch)
```

4. Hay que modificar el KillInterruptionHandler para que apague la maquina sólo cuando termine el ultimo proceso (solo podemos tocar el __Sistema Operativo__, sin modificar el __Hardware__)
