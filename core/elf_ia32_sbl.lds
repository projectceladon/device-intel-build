OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)

ENTRY(_entry)

SECTIONS
{
	. = CONFIG_LP_BASE_ADDRESS;

	. = ALIGN(16);
	_start = .;

	.text : {
		*(.text._entry)
		*(.text)
		*(.text.*)
	}

	.rodata : {
		*(.rodata)
		*(.rodata.*)
	}

	.data : {
		*(.data)
		*(.data.*)
	}

	_edata = .;

	.bss : {
		*(.sbss)
		*(.sbss.*)
		*(.bss)
		*(.bss.*)
		*(COMMON)

		/* Stack and heap */

		. = ALIGN(16);
		_heap = .;
		. += CONFIG_LP_HEAP_SIZE;
		. = ALIGN(16);
		_eheap = .;

		_estack = .;
		. += CONFIG_LP_STACK_SIZE;
		. = ALIGN(16);
		_stack = .;
	}

	_end = .;

	/DISCARD/ : {
		*(.comment)
		*(.note*)
	}
}
