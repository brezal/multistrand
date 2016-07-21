/*
 * m_options.h
 *
 *  Created on: Jun 12, 2016
 *      Author: Frits Dannenberg
 */

/* EnergyOption class header. This is currently a wrapper for the options set in python. */

#ifndef __ENERGYOPTIONS_H_
#define __ENERGYOPTIONS_H_

#include <python2.7/Python.h>
#include "ssystem.h"
#include "simoptions.h"
#include <vector>
#include <string>
#include <iostream>

#include "utility.h"

class EnergyOptions {
public:

	// construct methods
	void initializeArrheniusConstants();

// non-virtual getters
	double getTemperature(void);
	long getDangles(void);
	long getLogml(void);
	bool getGtenable(void);
	long getKineticRateMethod(void);
	double getJoinConcentration(void);
	bool usingArrhenius(void);

	double getBiScale(void);
	double getUniScale(void);

	string toString(void);
	static string primeRateToString(double);

	// virtual
	virtual bool compareSubstrateType(long) =0;
	virtual void getParameterFile(char*, PyObject*) = 0;

	// unprotected Arrhenius variables because we trust the user.
//	double AStack = 6.10;
//	double ALoop = 16.58;
//	double AEnd = 31.49;
//	double AStackLoop = 10.83;
//	double AStackEnd = 15.34;
//	double ALoopEnd = 8.55;
//	double AStackStack = 4.91;
//
//	double EStack = 0.75;
//	double ELoop = 5.84;
//	double EEnd = 12.38;
//	double EStackLoop = 3.83;
//	double EStackEnd = -0.43;
//	double ELoopEnd = 3.80;
//	double EStackStack = 6.57;



	double AStack = -0.1;
	double ALoop = -0.1;
	double AEnd = -0.1;
	double AStackLoop = -0.1;
	double AStackEnd = -0.1;
	double ALoopEnd = -0.1;
	double AStackStack = -0.1;

	double EStack = -0.1;
	double ELoop = -0.1;
	double EEnd = -0.1;
	double EStackLoop = -0.1;
	double EStackEnd = -0.1;
	double ELoopEnd = -0.1;
	double EStackStack = -0.1;


	static const double valuesPrime[MOVETYPE_SIZE];
	static const string MoveToString[MOVETYPE_SIZE];

	double AValues[MOVETYPE_SIZE] = { AEnd, ALoop, AStack, AStackStack, ALoopEnd, AStackEnd, AStackLoop };
	double EValues[MOVETYPE_SIZE] = { EEnd, ELoop, EStack, EStackStack, ELoopEnd, EStackEnd, EStackLoop };

	double dS_A = 1.02;
	double dS_C = 4.41;
	double dS_T = 0.55;
	double dS_G = -5.99;

	double alpha = 0.045;

protected:

	double temperature; // = 0NULL;
	long dangles; // = NULL;
	long logml; // = NULL;
	bool gtenable; // = NULL;
	long kinetic_rate_method; // = NULL;
	double joinConcentration; // = NULL;

	double biScale; // = NULL;
	double uniScale; // = NULL;

	// not sure if these are long
	long substrate_type; // = NULL;

	// Hard coding some default Arrhenius constants (for now)
	bool useArrRates = false;

};

class PEnergyOptions: public EnergyOptions {
public:
	//constructors
	PEnergyOptions(PyObject*);

	// implemented virtual
	bool compareSubstrateType(long);
	void getParameterFile(char*, PyObject*);

protected:
	PyObject* python_settings;

};

class CEnergyOptions: public EnergyOptions {
public:
	// constructors
	CEnergyOptions();

	// implemented virtual
	bool compareSubstrateType(long);
	void getParameterFile(char*, PyObject*);

protected:
	// empty

};

#endif /* __ENERGYOPTIONS_H_ */
