/* wts.js
*
*  Created 5/30/01
*  by Jon Beal
*
*  This module contains Javascript functions which are of use in WTS.  The
*  only functions currently residing here are those which try to trap a
*  double-click of the Save button, to prevent duplicate TRs from being
*  created.
*/

// Global variables:

last_called = null;	// remember when enoughTimeElapsed() was last called

// Functions:

function millisecondsSinceEpoch () {
	// Returns: the number of milliseconds which have elapsed since
	//	the epoch

	now = new Date();
	return now.getTime();
	}

function enoughTimeElapsed () {
	// Purpose: to determine if enough time has elapsed since the last
	//	time this function was called for it not to have been a
	//	double-click of the Save button
	// Returns: true if more than two seconds have elapsed, or false
	//	if not
	// Example: use this function in the onSubmit event of a form to
	//	ensure tha we do not process double-clicks as two separate
	//	form submissions, as in:
	//		<FORM ACTION="foo.cgi"
	//			onSubmit="return enoughTimeElapsed()">

	if (last_called == null)
		result = true;
	else {
		if (millisecondsSinceEpoch() - last_called < 2000) {
			window.alert ("Please remember not to double-click\
				the Save button.");
			result = false;
			}
		else
			result = true;
		}
	last_called = millisecondsSinceEpoch ();
	return result;
	}

// END wts.js
