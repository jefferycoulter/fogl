#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <GL/gl.h>
    typedef PROC (APIENTRY *PFNWGLGETPROCADDRESS)(LPCSTR);
    static HMODULE libgl = NULL;
    static PFNWGLGETPROCADDRESS wglGetProcAddressPtr = NULL;
    void* gl_get_proc_address(const char* name) 
    {
        if (!libgl) 
        {
            libgl = LoadLibraryA("opengl32.dll");
            wglGetProcAddressPtr = (PFNWGLGETPROCADDRESS)GetProcAddress(libgl, "wglGetProcAddress");
        }
        PROC p = NULL;
        if (wglGetProcAddressPtr) 
        {
            p = wglGetProcAddressPtr(name);
        }
        if (!p) 
        {
            p = GetProcAddress(libgl, name);
        }
        return (void*)p;
    }
    #elif __APPLE__
        #include <stdlib.h>
        #include <dlfcn.h>
        void* gl_get_proc_address(const char* name) 
        {
            static void* lib = NULL;
            if (!lib) 
            {
                lib = dlopen("/System/Library/Frameworks/OpenGL.framework/OpenGL", RTLD_LAZY);
            }
            return lib ? dlsym(lib, name) : NULL;
        }
    #else
        #include <GL/glx.h>
        void* gl_get_proc_address(const char* name) 
        {
            return (void*)glXGetProcAddress((const GLubyte*)name);
        }
#endif
