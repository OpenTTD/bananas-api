#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/**
 * Read and analyze a heightmap.
 *
 * This is done in C++, as there are no good libraries for this in Python.
 * opencv, Pillow, vips, etc, they all have their own issues. Most of them
 * read the PNG in full at once. vips is the exception, but doesn't allow
 * reading the palette.
 *
 * Reading the PNG in full at once is problematic, as a 16k by 16k heightmap
 * will consume 400+ MiB of RAM, which our backend simply doesn't have spare.
 *
 * Instead, do this in C++, using libpng directly. This has three advantages:
 * 1) It copies over the code used in OpenTTD, so we know it does the same.
 * 2) It uses very little memory, as the decoded PNG is actually never stored.
 * 3) It is fast, as iterations over long byte-strings is still very slow in Python.
 *
 * Arguments: bytes
 * Result: dict with "width", "height", "histogram", and "error".
 *   If "error" is non-empty, the rest of the values cannot be trusted.
 */
PyObject *HeightmapReadAndAnalyze(PyObject *self, PyObject *args);
