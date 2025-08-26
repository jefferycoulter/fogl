# fogl

fortran bindings for OpenGL.

### Setup
You need the gl.xml file provided by Khronos to generate the bindings.  The `download_gl_xml.py` script will do this for you, but it requires the `requests` module (generating the bindings doesn't have any dependencies, so this setup can be skipped if you just want to get the xml file yourself). Create a python environment and install the dependencies.
```
python3.12 -m venv env
source env/bin/activate
pip install -r requirements.txt
```
Then download the xml file by running
```
python scripts/download_gl_xml.py
```
This will put gl.xml in the root directory.

### Generate Bindings
To generate the bindings, you can then run
```
make
```
This will create a file called `gl_bindings_33.f90` in the root directory.  This can then be included in a fortran application to use OpenGL.  This runs the following python script:
```
python scripts/gen_gl_fortran.py --xml gl.xml --version 3.3 --profile core --out gl_bindings_33.f90 --strict-missing
```
If you would like to change any of the arguments then you can run with your modifications
```
python scripts/gen_gl_fortran.py --xml </path/to/gl.xml> --version <opengl-version> --profile <opengl-profile> --out <output-file-name> --strict-missing
```

### Running the demo
There is a demo (the triangle) in the `demo` directory.  After generating the bindings, you can build and run the demo with
```
make demo
make run
```
![triangle](https://github.com/jefferycoulter/fogl/blob/main/demo/img/triangle.png)
