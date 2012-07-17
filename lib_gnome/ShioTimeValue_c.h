/*
 *  ShioTimeValue_c.h
 *  gnome
 *
 *  Created by Generic Programmer on 3/13/12.
 *  Copyright 2012 __MyCompanyName__. All rights reserved.
 *
 */

#ifndef __ShioTimeValue_c__
#define __ShioTimeValue_c__

#include "Shio.h"
#include "OSSMTimeValue_c.h"

#define MAXNUMSHIOYEARS  20
#define MAXSTATIONNAMELEN  128
#define kMaxKeyedLineLength	1024

#ifndef pyGNOME
#include "TMover.h"
#else
#include "Mover_c.h"
#define TMover Mover_c
#endif

//enum { WIZ_POPUP = 1, WIZ_UNITS , WIZ_EDIT, WIZ_BMP, WIZ_HELPBUTTON };

/*typedef struct
{
	short year;// 1998, etc
	YEARDATAHDL yearDataHdl;
} ShioYearInfo;
*/
typedef struct
{
	Seconds time;
	double speedInKnots;
	short type;	// 0 -> MinBeforeFlood, 1 -> MaxFlood, 2 -> MinBeforeEbb, 3 -> MaxEbb
} EbbFloodData,*EbbFloodDataP,**EbbFloodDataH;

typedef struct
{
	Seconds time;
	double height;
	short type;	// 0 -> Low Tide, 1 -> High Tide
} HighLowData,*HighLowDataP,**HighLowDataH;

YEARDATAHDL GetYearData(short year);
YEARDATA2* ReadYearData(short year, const char *path, char *errStr);

class ShioTimeValue_c : virtual public OSSMTimeValue_c {

protected:

	// instance variables
	char fStationName[MAXSTATIONNAMELEN];
	char fStationType;
	double fLatitude;
	double fLongitude;
	CONSTITUENT2 fConstituent;
	HEIGHTOFFSET fHeightOffset;
	CURRENTOFFSET fCurrentOffset;
	//
	Boolean fHighLowValuesOpen; // for the list
	Boolean fEbbFloodValuesOpen; // for the list
	EbbFloodDataH fEbbFloodDataHdl;	// values to show on list for tidal currents
	HighLowDataH fHighLowDataHdl;	// values to show on list for tidal heights
	
	OSErr		GetKeyedValue(CHARH f, char*key, long lineNum, char* strLine,float *** val);
	OSErr 		GetKeyedValue(CHARH f, char*key, long lineNum, char* strLine,DATA * val);
	OSErr 		GetKeyedValue(CHARH f, char*key, long lineNum, char* strLine,short * val);
	OSErr 		GetKeyedValue(CHARH f, char*key, long lineNum, char* strLine,float * val);
	OSErr 		GetKeyedValue(CHARH f, char*key, long lineNum, char* strLine,double * val);
	OSErr		GetInterpolatedComponent (Seconds forTime, double *value, short index);
	OSErr		GetTimeChange (long a, long b, Seconds *dt);
	
	void 		ProgrammerError(char* routine);
	void 		InitInstanceVariables(void);
	
	long 		I_SHIOHIGHLOWS(void);
	long 		I_SHIOEBBFLOODS(void);
	
public:						
	
	bool	daylight_savings_off;	// AH 07/09/2012
	
							ShioTimeValue_c() { fEbbFloodDataHdl = 0; fHighLowDataHdl = 0; daylight_savings_off = true; timeValues = 0;}
							ShioTimeValue_c (TMover *theOwner);
							ShioTimeValue_c (TMover *theOwner,TimeValuePairH tvals);
	virtual ClassID 		GetClassID () { return TYPE_SHIOTIMEVALUES; }
	virtual Boolean			IAm(ClassID id) { if(id==TYPE_SHIOTIMEVALUES) return TRUE; return OSSMTimeValue_c::IAm(id); }
	virtual OSErr			ReadTimeValues (char *path);
	virtual long			GetNumEbbFloodValues ();	
	virtual long			GetNumHighLowValues ();
	virtual OSErr			GetTimeValue(const Seconds& start_time, const Seconds& end_time, const Seconds& current_time, VelocityRec *value);
	virtual WorldPoint		GetRefWorldPoint (void);
	
	virtual	double			GetDeriv (Seconds t1, double val1, Seconds t2, double val2, Seconds theTime);
	virtual	OSErr			GetConvertedHeightValue(Seconds forTime, VelocityRec *value);
	virtual	OSErr			GetProgressiveWaveValue(const Seconds& start_time, const Seconds& stop_time, const Seconds& current_time, VelocityRec *value);
#ifndef pyGNOME
	OSErr 					GetLocationInTideCycle(short *ebbFloodType, float *fraction);
#endif
	virtual OSErr			InitTimeFunc ();
			Boolean			DaylightSavingTimeInEffect(DateTimeRec *dateStdTime);	// AH 07/09/2012
	
	
};


#undef TMover
#endif