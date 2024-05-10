/*
   Python C Extension Module WiringPi OOK  
   
   Send OOK pulse train to digital gpio using wiringPi C library

   See: https://github.com/latchdevel/raspicode

   Copyright (c) 2022-2024 Jorge Rivera. All right reserved.
   License GNU Lesser General Public License v3.0.
*/

#include <Python.h>        // Entry point of the Python C API. C extensions should only #include <Python.h>
#include "wiringPi.h"      // Custom v2.71 Wiring library for Raspberry Pi (c) 2012-2017 Gordon Henderson (LGPL v3)

/* TX limits from https://github.com/latchdevel/pilight-usb-nano */
#define MAX_PULSE_LENGTH   100000   // Max pulse length (microseconds)
#define MAX_PULSE_COUNT      1000   // Max pulse count
#define MAX_TX_TIME          2000   // Max TX time (milliseconds)
#define MAX_TX_REPEATS         20   // Max TX repeats
#define DEFAULT_REPEATS         4   // Default TX repeats

/* Error return codes for tx(bcm_gpio, pulse_list, repeats = DEFAULT_REPEATS) */
#define NO_ERROR                      0
#define ERROR_UNKNOW                 -1
#define ERROR_INVALID_PULSE_COUNT    -2
#define ERROR_PULSETRAIN_OOD         -3
#define ERROR_INVALID_PULSE_LENGTH   -4
#define ERROR_INVALID_TX_TIME        -5

// Internal function
PyObject* tx_internal(PyObject* self, PyObject* args) {

   PyObject *pList;
   PyObject *pItem;
   Py_ssize_t pulse_count;

   int gpio     = -1;
   int repeats  =  DEFAULT_REPEATS;
   int result   =  NO_ERROR;

   uint32_t pulses[MAX_PULSE_COUNT] = {0};
   uint32_t tx_time = 0;
   int pulse;

   // Get function parameters
   if (!PyArg_ParseTuple(args, "iO!|i", &gpio, &PyList_Type, &pList, &repeats)){
      PyErr_SetString(PyExc_TypeError, "parameters are wrong.");
      return NULL;
   }

   // Parse function parameters (gpio)
   if ((gpio < 2) | (gpio > 27)){
      PyErr_SetString(PyExc_TypeError, "invalid gpio.");
      return NULL;
   }

   // Parse function parameters (repeats)
   if ((repeats < 1) | (repeats > MAX_TX_REPEATS)){
      PyErr_SetString(PyExc_TypeError, "invalid repeats.");
      return NULL;
   }

   // Parse function parameters (list of pulses)
   pulse_count = PyList_Size(pList);

   if ((pulse_count < 1) | (pulse_count > MAX_PULSE_COUNT)){
      result = ERROR_INVALID_PULSE_COUNT;
   }else{
      if (pulse_count % 2 != 0){
         result = ERROR_PULSETRAIN_OOD;
      }else{
         for (int i=0; i<pulse_count; i++) {
            pItem = PyList_GetItem(pList, i);
            if(!PyLong_Check(pItem)) {
               PyErr_SetString(PyExc_TypeError, "list items must be integers.");
               return NULL;
            }else{
               pulse = PyLong_AsLong(pItem);
               if ((pulse > 0) & (pulse <= MAX_PULSE_LENGTH)){
                  pulses[i]=(uint32_t)pulse;
                  tx_time = tx_time + pulses[i];
                  if (tx_time > MAX_TX_TIME*1000){
                     result = ERROR_INVALID_TX_TIME;
                     break;
                  }
               }else{
                  result = ERROR_INVALID_PULSE_LENGTH;
                  break;
               }
            }
         }
      }
   }

   if (result == NO_ERROR){

      // Begin TX
      
      // Setup GPIO output
      pinMode(gpio, OUTPUT);

      // Get initial time
      result = millis();

      // Repeats loop
      for (int r=0; r < repeats; r++ ){

         // Pulses loop
         for (int i=0; i<pulse_count; i++){
            
            // Set GPIO state (HIGH for odd pulse index or LOW for even pulse index)
            digitalWrite(gpio,!(i%2));

            // Delay pulse length
            delayMicrosecondsHard(pulses[i]);

         }

         // Check if exceed max TX time
         if (millis() > (uint32_t)result + MAX_TX_TIME){
            break;
         }
         
      } 

      // Get final time
      result = millis() - result;

      // Ensure gpio output low on completion
      digitalWrite(gpio,LOW);
   }
   
   return Py_BuildValue("i",result);
}

// Python function definition
PyMethodDef wiringpiook_funcs[] = {
	{"tx", (PyCFunction)tx_internal, METH_VARARGS, "tx(bcm_gpio, [pulse_length,pulse_length,...], repeats = DEFAULT_REPEATS)."},
	{NULL}
};

// Python module definition
PyModuleDef wiringpiook_mod = {
	PyModuleDef_HEAD_INIT, "wiringpiook", "Wiring PI OOK module.", -1, wiringpiook_funcs, NULL, NULL, NULL, NULL
};

// Python module initialization
PyMODINIT_FUNC PyInit_wiringpiook(void) {
   /*
      Initializes wiringPi at module import
      Pin number in this mode is the native Broadcom GPIO numbers (Broadcom SOC channel).
      See: http://wiringpi.com/reference/setup/
   */

   if (wiringPiSetupGpio() == -1){
      PyErr_SetString(PyExc_TypeError, "unable to init wiringPiSetupGpio().");
      return NULL;
   }

	return PyModule_Create(&wiringpiook_mod);
}
