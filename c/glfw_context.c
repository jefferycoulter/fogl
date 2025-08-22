#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <stdio.h>

static GLFWwindow* g_win = NULL;

int create_glfw_context_33_core(int w, int h, const char* title) 
{
    if (!glfwInit())
    {
        return 0;
    }
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#if __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE);
#endif
    g_win = glfwCreateWindow(w, h, title, NULL, NULL);
    if (!g_win)
    {
        glfwTerminate(); return 0;
    }
    glfwMakeContextCurrent(g_win);
    return 1;
}

void glfw_swap()
{ 
    if (g_win) 
    {
        glfwSwapBuffers(g_win);
    }
}

void glfw_poll()
{
    glfwPollEvents();
}

int glfw_should_close()
{
    return g_win && glfwWindowShouldClose(g_win);
}

void destroy_glfw() 
{
    if (g_win)
    {
        glfwDestroyWindow(g_win); glfwTerminate();
    }
}