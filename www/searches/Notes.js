/* notes.js
*
*  Created 5/30/01
*  by Jon Beal
* 
*  This module contains Javascript functions which help WTS work with text
*  field templates & pull-downs to work with them in different ways.
* 
*  Notes:
*  1) use of this module requires that an array of strings named 'template'
* 	be defined elsewhere, mapping an integer array index (_Template_key)
* 	to the text of the template (value)
*/

// Functions:

function timestamp() {
	// Returns: a string containing the current date and time in the
	//	format "mm/dd/yyyy hh:mm"

	now = new Date();
	now.getTime();
	year = String(now.getYear());
	if (year.length > 2)
		year = year.slice (year.length - 2);
	return (now.getMonth() + 1) + "/" +
		now.getDate() + "/" +
		year + " " +
		now.getHours() + ":" +
		now.getMinutes();
	}

function undoNotes (
	field,		// object reference to the target text field
	button		// object reference to the undo/redo button
	) {
	// Purpose: reverts the value of 'field' back to its previous value,
	//	and changes the label on the 'button' from 'Undo' to 'Redo'
	//	or vice versa

	temp = field.value;
	field.value = field.previous_value;
	field.previous_value = temp;

	if (button.value == 'Undo')
		button.value = 'Redo'
	else
		button.value = 'Undo'
	}

function doSubstitutions (s, tr_nr) {
	var t = s;
	t = t.replace (/.timestamp./, timestamp());
	t = t.replace (/.TR./, tr_nr);
	return t;
	}

function doNotes (
	op,		// string; specifies the operation to be performed
	template_key,	// string; specifies the type of template to use
	template_set,	// object reference to array of templates to look in
	field,		// object reference to the text field in question
	UndoButton,	// object reference to the Undo/Redo button
	tr_nr		// tracking record number
	) {
	// Purpose: update the given 'field' with the template specified by
	//	'template_key' using the operation specified in 'op'.  And,
	//	set the Undo/Redo button to 'Undo'

	field.previous_value = field.value;	// prepare for future Undo
	UndoButton.value = 'Undo';

	// compute in 's' the proper string based on the given 'template_key'

	if (template_key < template_set.length)
		s = doSubstitutions(template_set[template_key], tr_nr)
	else
		s = '';

	// update 'field' with the value we computed in 's'

	switch (op) {
		case "replace" :
			field.value = s;
			break;
		case "append" :
			field.value = field.value + s;
			break;
		case "insert" :
			field.value = field.value.replace (/\*\*/, s);
			if (field.value == field.previous_value)
				alert ('Could not find **.  Please place **\
					where you would like to insert the\
					template.');
			break;
		default :
			break;
		}
	}

// END notes.js
