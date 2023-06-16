#include "_bananas_api.h"

static PyMethodDef BananasApiMethods[] = {
	{"heightmap", HeightmapReadAndAnalyze, METH_VARARGS, "Read and analyze a heightmap."},
	{nullptr, nullptr, 0, nullptr}
};

static struct PyModuleDef module = { PyModuleDef_HEAD_INIT, "_bananas_api", nullptr, -1, BananasApiMethods };

PyMODINIT_FUNC
PyInit__bananas_api(void)
{
	return PyModule_Create(&module);
}
