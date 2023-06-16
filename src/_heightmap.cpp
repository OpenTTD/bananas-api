#include "_bananas_api.h"

#include <png.h>
#include <string>

static constexpr Py_ssize_t CHUNK_SIZE = 1024;
static constexpr int HISTOGRAM_SIZE = 256;

struct HeightmapResult {
	/* Internal variables. */
	bool has_palette = false;
	bool is_interlaced = false;
	uint8_t channels = 0;
	uint8_t gray_palette[256] = {};

	/* Returning variables. */
	uint32_t width = 0;
	uint32_t height = 0;
	uint32_t histogram[HISTOGRAM_SIZE] = {};
	std::string error = "";

	PyObject *ToPyObject()
	{
		auto list = PyList_New(HISTOGRAM_SIZE);
		for (int i = 0; i < HISTOGRAM_SIZE; i++) {
			PyList_SetItem(list, i, PyLong_FromLong(this->histogram[i]));
		}

		return Py_BuildValue(
			"{s:s,s:i,s:i,s:O}",
			"error", this->error.c_str(),
			"width", this->width,
			"height", this->height,
			"histogram", list
		);
	}
};

/* The following code is based on https://github.com/OpenTTD/OpenTTD/blob/master/src/heightmap.cpp */
static inline uint8_t RGBToGrayscale(uint8_t red, uint8_t green, uint8_t blue)
{
	return ((red * 19595) + (green * 38470) + (blue * 7471)) / 65536;
}

static void HeightmapCallbackRow(png_structp png_ptr, png_bytep new_row, png_uint_32 row_num, int pass)
{
	HeightmapResult *result = reinterpret_cast<HeightmapResult *>(png_get_progressive_ptr(png_ptr));

	/* No updated for interlaced. */
	if (new_row == nullptr) {
		return;
	}

	/* Interlaced has different amount of pixels set depending on the pass.
	* As we only care about the pixels, and not their location, we can just
	* adjust the size we read. */
	auto size = result->width;
	if (result->is_interlaced) {
		switch (pass) {
			case 0: size = (size + 7) / 8; break;
			case 1: size = (size + 3) / 8; break;
			case 2: size = (size + 3) / 4; break;
			case 3: size = (size + 1) / 4; break;
			case 4: size = (size + 1) / 2; break;
			case 5: size = (size + 0) / 2; break;
			case 6: size = (size + 0) / 1; break;
			default: return;
		}
	}

	/* The following code is based on https://github.com/OpenTTD/OpenTTD/blob/master/src/heightmap.cpp */
	for (uint32_t x = 0; x < size; x++) {
		uint x_offset = x * result->channels;

		uint8_t pixel;
		if (result->has_palette) {
			pixel = result->gray_palette[new_row[x_offset]];
		} else if (result->channels == 3) {
			pixel = RGBToGrayscale(new_row[x_offset + 0], new_row[x_offset + 1], new_row[x_offset + 2]);
		} else {
			pixel = new_row[x_offset];
		}

		result->histogram[pixel] += 1;
	}
}

static void HeightmapCallbackInfo(png_structp png_ptr, png_infop info_ptr)
{
	HeightmapResult *result = reinterpret_cast<HeightmapResult *>(png_get_progressive_ptr(png_ptr));

	png_set_packing(png_ptr);
	png_set_strip_alpha(png_ptr);
	png_set_strip_16(png_ptr);
	png_read_update_info(png_ptr, info_ptr);

	if ((png_get_channels(png_ptr, info_ptr) != 1) && (png_get_channels(png_ptr, info_ptr) != 3) && (png_get_bit_depth(png_ptr, info_ptr) != 8)) {
		result->error = "PNG uses unsupported channels or bit depth.";
		return;
	}
	if (png_get_interlace_type(png_ptr, info_ptr) != PNG_INTERLACE_NONE && png_get_channels(png_ptr, info_ptr) != 1) {
		result->error = "Interlaced PNGs with more than one channel are not supported.";
		return;
	}

	result->width = png_get_image_width(png_ptr, info_ptr);
	result->height = png_get_image_height(png_ptr, info_ptr);

	if (result->width * result->height > 16384 * 16384) {
		result->error = "Image is too large.";
		return;
	}

	result->is_interlaced = png_get_interlace_type(png_ptr, info_ptr) != PNG_INTERLACE_NONE;
	result->has_palette = png_get_color_type(png_ptr, info_ptr) == PNG_COLOR_TYPE_PALETTE;
	result->channels = png_get_channels(png_ptr, info_ptr);

	/* The following code is based on https://github.com/OpenTTD/OpenTTD/blob/master/src/heightmap.cpp */
	if (result->has_palette) {
		int i;
		int palette_size;
		png_color *palette;
		bool all_gray = true;

		png_get_PLTE(png_ptr, info_ptr, &palette, &palette_size);
		for (i = 0; i < palette_size && (palette_size != 16 || all_gray); i++) {
			all_gray &= palette[i].red == palette[i].green && palette[i].red == palette[i].blue;
			result->gray_palette[i] = RGBToGrayscale(palette[i].red, palette[i].green, palette[i].blue);
		}

		/**
		 * For a non-gray palette of size 16 we assume that
		 * the order of the palette determines the height;
		 * the first entry is the sea (level 0), the second one
		 * level 1, etc.
		 */
		if (palette_size == 16 && !all_gray) {
			for (i = 0; i < palette_size; i++) {
				result->gray_palette[i] = 256 * i / palette_size;
			}
		}
	}
}

PyObject *HeightmapReadAndAnalyze(PyObject *self, PyObject *args)
{
	HeightmapResult result = {};

	unsigned char *png_bytes;
	Py_ssize_t png_length;

	/* We expect one argument: bytes. */
	if (!PyArg_ParseTuple(args, "y#", &png_bytes, &png_length)) {
		result.error = "Invalid arguments.";
		return result.ToPyObject();
	}

	/* Make sure this is actually a PNG. */
	if (png_length < 4 || png_sig_cmp(png_bytes, 0, 4) != 0) {
		result.error = "File is not a PNG image.";
		return result.ToPyObject();
	}

	auto png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);
	if (png_ptr == nullptr) {
		result.error = "Failed to create PNG read struct.";
		return result.ToPyObject();
	}
	auto info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == nullptr || setjmp(png_jmpbuf(png_ptr))) {
		result.error = "Failed to create PNG info struct.";
		png_destroy_read_struct(&png_ptr, &info_ptr, nullptr);
		return result.ToPyObject();
	}

	/* Use progressive reading, so we never actually store the final result. */
	png_set_progressive_read_fn(png_ptr, &result, HeightmapCallbackInfo, HeightmapCallbackRow, nullptr);

	/* Read the buffer till it is empty. */
	while (png_length > 0) {
		auto remainder = std::min(CHUNK_SIZE, png_length);

		png_process_data(png_ptr, info_ptr, png_bytes, remainder);

		png_bytes += remainder;
		png_length -= remainder;
	}

	png_destroy_read_struct(&png_ptr, &info_ptr, nullptr);
	return result.ToPyObject();
}
