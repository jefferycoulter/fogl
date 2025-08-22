program triangle_demo
  	use iso_c_binding
  	use gl_bindings_33_core 	! generated file name from the script
  	implicit none

  	interface
     	function create_glfw_context_33_core(w,h,title) bind(C, name="create_glfw_context_33_core") result(ok)
       		import :: c_int, c_char
       		integer(c_int), value :: w, h
       		character(kind=c_char), dimension(*) :: title
       		integer(c_int) :: ok
     	end function
     	subroutine glfw_swap() bind(C)
     	end subroutine
     	subroutine glfw_poll() bind(C)
     	end subroutine
     	function glfw_should_close() bind(C) result(flag)
       		import :: c_int
       		integer(c_int) :: flag
     	end function
     	subroutine destroy_glfw() bind(C)
     	end subroutine
  	end interface

  	character(kind=c_char), allocatable :: zt(:)
  	integer(c_int) :: ok
  	integer(c_int), target :: prog, vs, fs, vao, vbo
  	real(c_float), dimension(9), target :: verts
  	character(len=:), allocatable :: vsrc, fsrc

	call to_cstr("Fortran GL Triangle", zt)
	ok = create_glfw_context_33_core(800_c_int, 600_c_int, zt)
	if (ok == 0_c_int) stop "Failed to create GLFW context"

	call glLoadFunctions()

	vsrc = &
	"#version 330 core"//achar(10)//  &
	"layout(location=0) in vec3 aPos;"//achar(10)//  &
	"void main(){ gl_Position = vec4(aPos,1.0); }"//achar(10)
	fsrc = &
	"#version 330 core"//achar(10)// &
	"out vec4 FragColor;"//achar(10)// &
	"void main(){ FragColor = vec4(1.0,0.7,0.2,1.0); }"//achar(10)

	vs = p_glCreateShader(GL_VERTEX_SHADER)
	call set_shader_source(vs, vsrc)
	call p_glCompileShader(vs)
	call check_shader(vs, "vertex")

	fs = p_glCreateShader(GL_FRAGMENT_SHADER)
	call set_shader_source(fs, fsrc)
	call p_glCompileShader(fs)
	call check_shader(fs, "fragment")

	prog = p_glCreateProgram()
	call p_glAttachShader(prog, vs)
	call p_glAttachShader(prog, fs)
	call p_glLinkProgram(prog)
	call check_program(prog)

	call p_glDeleteShader(vs)
	call p_glDeleteShader(fs)

	verts = [ -0.5_c_float, -0.5_c_float, 0.0_c_float,  &
				0.5_c_float, -0.5_c_float, 0.0_c_float,  &
				0.0_c_float,  0.5_c_float, 0.0_c_float ]

	call p_glGenVertexArrays(1_c_int, c_loc(vao))
	call p_glGenBuffers(1_c_int, c_loc(vbo))

	call p_glBindVertexArray(vao)
	call p_glBindBuffer(GL_ARRAY_BUFFER, vbo)
	call p_glBufferData(GL_ARRAY_BUFFER, int(9*4,c_long_long), c_loc(verts(1)), GL_STATIC_DRAW)
	call p_glVertexAttribPointer(0_c_int, 3_c_int, GL_FLOAT, 0_c_int, 0_c_int, c_null_ptr)
	call p_glEnableVertexAttribArray(0_c_int)
	call p_glBindBuffer(GL_ARRAY_BUFFER, 0_c_int)
	call p_glBindVertexArray(0_c_int)

	call p_glViewport(0_c_int, 0_c_int, 800_c_int, 600_c_int)
	call p_glClearColor(0.4_c_float, 0.4_c_float, 0.4_c_float, 1.0_c_float)

	do while (glfw_should_close() == 0_c_int)
		call p_glClear(GL_COLOR_BUFFER_BIT)
		call p_glUseProgram(prog)
		call p_glBindVertexArray(vao)
		call p_glDrawArrays(GL_TRIANGLES, 0_c_int, 3_c_int)
		call glfw_swap()
		call glfw_poll()
	end do

	call p_glDeleteVertexArrays(1_c_int, c_loc(vao))
	call p_glDeleteBuffers(1_c_int, c_loc(vbo))
	call p_glDeleteProgram(prog)
	call destroy_glfw()

contains
  	subroutine set_shader_source(shader, src)
		use iso_c_binding
		integer(c_int), intent(in) :: shader
		character(len=*), intent(in) :: src
		character(kind=c_char), allocatable, target :: zsrc(:)
		type(c_ptr), target :: cstrs(1)
		integer(c_int), target :: lens(1)
		call to_cstr(src, zsrc)
		cstrs(1) = c_loc(zsrc(0))
		lens(1)  = len_trim(src)
		call p_glShaderSource(shader, 1_c_int, c_loc(cstrs(1)), c_loc(lens(1)))
	end subroutine

  	subroutine check_shader(sid, label)
    	use iso_c_binding
    	integer(c_int), intent(in) :: sid
		character(len=*), intent(in) :: label
		integer(c_int), target :: status, loglen
		character(kind=c_char), allocatable, target :: buf(:)
		call p_glGetShaderiv(sid, GL_COMPILE_STATUS, c_loc(status))
    	if (status == 0_c_int) then
			call p_glGetShaderiv(sid, GL_INFO_LOG_LENGTH, c_loc(loglen))
			if (loglen < 1) loglen = 1024
			allocate(buf(0:loglen))
			call p_glGetShaderInfoLog(sid, loglen, c_loc(loglen), c_loc(buf(0)))
			print *, trim(label)//" shader error:"
			call print_cstr(buf)
			stop 1
    	end if
  	end subroutine

  	subroutine check_program(pid)
		use iso_c_binding
		integer(c_int), intent(in) :: pid
		integer(c_int), target :: status, loglen
		character(kind=c_char), allocatable, target :: buf(:)
		call p_glGetProgramiv(pid, GL_LINK_STATUS, c_loc(status))
		if (status == 0_c_int) then
			call p_glGetProgramiv(pid, GL_INFO_LOG_LENGTH, c_loc(loglen))
			if (loglen < 1) loglen = 1024
			allocate(buf(0:loglen))
			call p_glGetProgramInfoLog(pid, loglen, c_loc(loglen), c_loc(buf(0)))
			print *, "program link error:"
			call print_cstr(buf)
			stop 1
    	end if
  	end subroutine

  	subroutine print_cstr(s)
    	character(kind=c_char), intent(in) :: s(0:)
    	integer :: i, n
    	n = size(s)
    	do i = 0, n-1
       		if (s(i) == c_null_char) exit
       		write(*,'(A)',advance='no') transfer(s(i), ' ')
		end do
		write(*,*)
  	end subroutine
end program
