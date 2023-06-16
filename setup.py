from distutils.core import setup, Extension

def main():
    setup(name="bananas-api",
          version="1.0.0",
          ext_modules=[Extension("_bananas_api", ["src/_bananas_api.cpp", "src/_heightmap.cpp"], libraries=["png", "z"])])

if __name__ == "__main__":
    main()
